"""
JTech Tally Bridge - GSTR-3B summary

GSTR-3B = monthly summary return. Builds on GSTR-1 outward supplies
plus inward supplies (purchases) for ITC reconciliation.

Sections:
  3.1 Outward supplies (taxable + IGST + CGST + SGST + Cess)
      (a) B2B           (b) B2C large      (c) Exports
      (d) Nil/exempt    (e) Reverse charge
  3.2 ITC breakdown (ITC available on inward supplies)
  4.    TDS/TCS received
  5.    Inward supplies liable to reverse charge
"""

from datetime import date
from typing import Optional

from core.company_context import get_current_company_id
from storage.database import get_connection
from storage.repositories.voucher_repo import save_report_snapshot
from config.logging_config import get_logger

log = get_logger(__name__)


INWARD_VOUCHER_TYPES = ("Purchase", "Debit Note")


def _default_period(d_from, d_to):
    if d_from and d_to:
        return d_from, d_to
    today = date.today()
    if today.month >= 4:
        return date(today.year, 4, 1), date(today.year + 1, 3, 31)
    return date(today.year - 1, 4, 1), date(today.year, 3, 31)


def _load_inward_vouchers(company_id, d_from, d_to):
    df_str = d_from.strftime("%Y%m%d")
    dt_str = d_to.strftime("%Y%m%d")
    placeholders = ",".join(["?"] * len(INWARD_VOUCHER_TYPES))

    sql = f"""
        SELECT v.id, v.voucher_type, v.voucher_number, v.voucher_date,
               v.party, v.party_gstin, v.amount
        FROM vouchers v
        WHERE v.company_id = ?
          AND v.voucher_date >= ?
          AND v.voucher_date <= ?
          AND v.voucher_type IN ({placeholders})
    """
    with get_connection() as conn:
        rows = [dict(r) for r in conn.execute(
            sql, [company_id, df_str, dt_str, *INWARD_VOUCHER_TYPES]
        ).fetchall()]
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


def generate_gstr3b(date_from=None, date_to=None):
    """Generate GSTR-3B summary for the period."""

    company_id = get_current_company_id()
    d_from, d_to = _default_period(date_from, date_to)

    # Reuse GSTR-1 for outward supplies
    from reports.gstr1 import generate_gstr1
    gstr1 = generate_gstr1(d_from, d_to)

    outward_totals = gstr1["grand_total"]

    # Inward supplies for ITC
    inward_vouchers, inward_via = _load_inward_vouchers(
        company_id, d_from, d_to
    )

    itc = {
        "igst": 0.0,
        "cgst": 0.0,
        "sgst": 0.0,
        "cess": 0.0,
        "taxable_value": 0.0,
    }
    for via in inward_via:
        itc["igst"] += via.get("igst_amount") or 0.0
        itc["cgst"] += via.get("cgst_amount") or 0.0
        itc["sgst"] += via.get("sgst_amount") or 0.0
        itc["cess"] += via.get("cess_amount") or 0.0
        itc["taxable_value"] += abs(via.get("amount") or 0.0)

    for k in itc:
        itc[k] = round(itc[k], 2)

    result = {
        "company_id": company_id,
        "from": d_from.isoformat(),
        "to": d_to.isoformat(),
        "section_3_1_outward_supplies": {
            "taxable_value": outward_totals["taxable_value"],
            "igst": outward_totals["igst"],
            "cgst": outward_totals["cgst"],
            "sgst": outward_totals["sgst"],
            "cess": outward_totals["cess"],
            "total_tax": round(
                outward_totals["igst"] + outward_totals["cgst"]
                + outward_totals["sgst"] + outward_totals["cess"], 2
            ),
        },
        "section_3_2_itc": itc,
        "section_4_tds_tcs": {
            "tds_received": 0.0,
            "tcs_received": 0.0,
            "note": "TDS/TCS requires additional extraction. Currently zero.",
        },
        "section_5_reverse_charge": {
            "inward_value": 0.0,
            "note": "Reverse charge tracking requires voucher-level flag.",
        },
        "net_tax_payable": round(
            outward_totals["igst"] + outward_totals["cgst"]
            + outward_totals["sgst"] + outward_totals["cess"]
            - itc["igst"] - itc["cgst"] - itc["sgst"] - itc["cess"],
            2,
        ),
        "note": (
            "GSTR-3B is a summary return. Net tax payable = output tax - ITC. "
            "Reverse charge and TDS/TCS sections require additional voucher "
            "extraction work."
        ),
    }

    save_report_snapshot(
        company_id=company_id,
        report_type="gstr3b",
        result=result,
        params={"from": d_from.isoformat(), "to": d_to.isoformat()},
    )
    return result
