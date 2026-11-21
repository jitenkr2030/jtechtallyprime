"""
JTech Tally Bridge - GSTR-1 report

GSTR-1 = outward supplies (sales) return. Filed monthly by every
GST-registered business. Categories:

  4.  B2B Invoices        - taxable, recipient is GSTIN-registered
  5.  B2C (Large)         - taxable, value > 2.5 lakh, intra/inter-state
  6.  B2C (Small)         - taxable, value <= 2.5 lakh, consolidated
  7.  Credit/Debit Notes  - against outward supplies
  8.  Exports             - with/without payment of tax
  9.  Nil-rated / Exempt  - consolidated
  10. HSN Summary         - HSN-wise outward supply
  11. Documents Issued    - voucher type-wise count

This module aggregates vouchers from the SQLite store that were
imported with GST fields captured (party_gstin, place_of_supply,
inventory allocations with hsn_code and cgst/sgst/igst amounts).
"""

from datetime import date, datetime
from typing import Optional

from core.company_context import get_current_company_id
from storage.database import get_connection
from storage.repositories.voucher_repo import save_report_snapshot
from config.logging_config import get_logger

log = get_logger(__name__)


OUTWARD_VOUCHER_TYPES = ("Sales", "Credit Note")
EXPORT_VOUCHER_TYPES = ("Sales",)  # exports are sales with foreign party
CDN_VOUCHER_TYPES = ("Credit Note", "Debit Note")


def _default_period(d_from, d_to):
    if d_from and d_to:
        return d_from, d_to
    today = date.today()
    if today.month >= 4:
        return date(today.year, 4, 1), date(today.year + 1, 3, 31)
    return date(today.year - 1, 4, 1), date(today.year, 3, 31)


def _is_registered_gstin(gstin):
    if not gstin:
        return False
    s = str(gstin).strip().upper()
    # GSTIN format: 2-digit state code + 10-char PAN + 1 entity + Z + 1
    return len(s) == 15 and s.endswith("Z") and s[:2].isdigit()


def _state_code_from_gstin(gstin):
    if not gstin or len(str(gstin)) < 2:
        return None
    try:
        return int(str(gstin)[:2])
    except ValueError:
        return None


def _load_outward_vouchers(company_id, d_from, d_to):
    df_str = d_from.strftime("%Y%m%d")
    dt_str = d_to.strftime("%Y%m%d")

    placeholders = ",".join(["?"] * len(OUTWARD_VOUCHER_TYPES))
    sql = f"""
        SELECT v.id, v.voucher_type, v.voucher_number, v.voucher_date,
               v.party, v.party_gstin, v.place_of_supply,
               v.amount, v.gst_registration_type
        FROM vouchers v
        WHERE v.company_id = ?
          AND v.voucher_date >= ?
          AND v.voucher_date <= ?
          AND v.voucher_type IN ({placeholders})
        ORDER BY v.voucher_date, v.voucher_number
    """
    with get_connection() as conn:
        rows = [dict(r) for r in conn.execute(
            sql, [company_id, df_str, dt_str, *OUTWARD_VOUCHER_TYPES]
        ).fetchall()]
        # Pull inventory allocations for each voucher in one query
        if rows:
            v_ids = [r["id"] for r in rows]
            via_rows = conn.execute(
                f"""
                SELECT * FROM voucher_inventory_allocations
                WHERE voucher_id IN ({",".join(["?"] * len(v_ids))})
                """,
                v_ids,
            ).fetchall()
        else:
            via_rows = []
    return rows, [dict(r) for r in via_rows]


def _bucket_invoice(voucher, via_for_voucher, company_state_code):
    """
    Categorize one outward voucher into GSTR-1 sections.
    Returns dict { section, taxable_value, igst, cgst, sgst, cess }.
    """

    party_gstin = voucher.get("party_gstin")
    is_b2b = _is_registered_gstin(party_gstin)

    total_taxable = 0.0
    total_igst = 0.0
    total_cgst = 0.0
    total_sgst = 0.0
    total_cess = 0.0

    for via in via_for_voucher:
        total_taxable += abs(via.get("amount") or 0.0)
        total_igst += via.get("igst_amount") or 0.0
        total_cgst += via.get("cgst_amount") or 0.0
        total_sgst += via.get("sgst_amount") or 0.0
        total_cess += via.get("cess_amount") or 0.0

    if total_taxable == 0:
        # Fallback to voucher amount if inventory lines absent
        total_taxable = (voucher.get("amount") or 0.0) - (
            total_igst + total_cgst + total_sgst + total_cess
        )

    # Determine section
    if not (total_igst + total_cgst + total_sgst + total_cess) > 0:
        section = "nil_rated"
    elif is_b2b:
        section = "b2b"
    elif total_taxable > 250000:
        section = "b2c_large"
    else:
        section = "b2c_small"

    return {
        "voucher_id": voucher["id"],
        "voucher_type": voucher["voucher_type"],
        "voucher_number": voucher["voucher_number"],
        "voucher_date": voucher["voucher_date"],
        "party": voucher.get("party"),
        "party_gstin": party_gstin,
        "section": section,
        "taxable_value": round(total_taxable, 2),
        "igst": round(total_igst, 2),
        "cgst": round(total_cgst, 2),
        "sgst": round(total_sgst, 2),
        "cess": round(total_cess, 2),
        "total_invoice": round(
            total_taxable + total_igst + total_cgst + total_sgst + total_cess, 2
        ),
    }


def _build_hsn_summary(invoices_with_via):
    """HSN-wise outward supply summary."""

    hsn_map = {}
    for inv in invoices_with_via:
        for via in inv["_via"]:
            hsn = via.get("hsn_code") or "UNKNOWN"
            rate = via.get("gst_rate")
            key = (hsn, rate)
            entry = hsn_map.setdefault(key, {
                "hsn_code": hsn,
                "gst_rate": rate,
                "qty": 0.0,
                "taxable_value": 0.0,
                "igst": 0.0,
                "cgst": 0.0,
                "sgst": 0.0,
                "cess": 0.0,
                "invoice_count": 0,
            })
            entry["qty"] += abs(via.get("qty") or 0.0)
            entry["taxable_value"] += abs(via.get("amount") or 0.0)
            entry["igst"] += via.get("igst_amount") or 0.0
            entry["cgst"] += via.get("cgst_amount") or 0.0
            entry["sgst"] += via.get("sgst_amount") or 0.0
            entry["cess"] += via.get("cess_amount") or 0.0
            entry["invoice_count"] += 1
    return [
        {
            "hsn_code": v["hsn_code"],
            "gst_rate": v["gst_rate"],
            "qty": round(v["qty"], 3),
            "taxable_value": round(v["taxable_value"], 2),
            "igst": round(v["igst"], 2),
            "cgst": round(v["cgst"], 2),
            "sgst": round(v["sgst"], 2),
            "cess": round(v["cess"], 2),
            "invoice_count": v["invoice_count"],
        }
        for v in hsn_map.values()
    ]


def generate_gstr1(date_from=None, date_to=None):
    """Generate GSTR-1 return data for the period."""

    company_id = get_current_company_id()
    d_from, d_to = _default_period(date_from, date_to)

    log.info(
        "Generating GSTR-1 for company=%s period=%s..%s",
        company_id, d_from, d_to,
    )

    vouchers, via_rows = _load_outward_vouchers(company_id, d_from, d_to)

    # Group inventory allocations by voucher_id
    via_by_voucher = {}
    for via in via_rows:
        via_by_voucher.setdefault(via["voucher_id"], []).append(via)

    # Bucket each invoice
    bucketed = []
    for v in vouchers:
        via_for_v = via_by_voucher.get(v["id"], [])
        b = _bucket_invoice(v, via_for_v, company_state_code=None)
        b["_via"] = via_for_v  # for HSN summary
        bucketed.append(b)

    sections = {
        "b2b": [],
        "b2c_large": [],
        "b2c_small": [],
        "nil_rated": [],
    }
    for b in bucketed:
        sections.setdefault(b["section"], []).append(b)

    # Strip internal _via from final output
    for section, items in sections.items():
        for item in items:
            item.pop("_via", None)

    hsn_summary = _build_hsn_summary(
        [{"_via": via_by_voucher.get(b["voucher_id"], [])}
         for b in bucketed]
    )

    # Section-wise totals
    section_totals = {}
    for section, items in sections.items():
        section_totals[section] = {
            "count": len(items),
            "taxable_value": round(sum(i["taxable_value"] for i in items), 2),
            "igst": round(sum(i["igst"] for i in items), 2),
            "cgst": round(sum(i["cgst"] for i in items), 2),
            "sgst": round(sum(i["sgst"] for i in items), 2),
            "cess": round(sum(i["cess"] for i in items), 2),
            "total": round(sum(i["total_invoice"] for i in items), 2),
        }

    result = {
        "company_id": company_id,
        "from": d_from.isoformat(),
        "to": d_to.isoformat(),
        "sections": sections,
        "section_totals": section_totals,
        "hsn_summary": hsn_summary,
        "grand_total": {
            "taxable_value": round(
                sum(s["taxable_value"] for s in section_totals.values()), 2
            ),
            "igst": round(
                sum(s["igst"] for s in section_totals.values()), 2
            ),
            "cgst": round(
                sum(s["cgst"] for s in section_totals.values()), 2
            ),
            "sgst": round(
                sum(s["sgst"] for s in section_totals.values()), 2
            ),
            "cess": round(
                sum(s["cess"] for s in section_totals.values()), 2
            ),
        },
        "note": (
            "B2B/B2C classification requires party GSTIN to be captured. "
            "HSN summary requires inventory allocations with hsn_code set. "
            "If sections appear empty, verify GST fields are populated in "
            "voucher_inventory_allocations."
        ),
    }

    save_report_snapshot(
        company_id=company_id,
        report_type="gstr1",
        result=result,
        params={"from": d_from.isoformat(), "to": d_to.isoformat()},
    )
    return result
