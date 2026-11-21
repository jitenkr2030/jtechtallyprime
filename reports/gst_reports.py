"""
JTech Tally Bridge - GST Reports (skeleton)

Aggregates GST-relevant vouchers (Sales, Purchase, Credit Note,
Debit Note) into a summary by rate slab.

Note: Tally stores GST registration type, HSN, and rate inside the
voucher inventory lines. For a complete GST return (GSTR-1 / GSTR-3B)
this module must be extended with the rate field from
VOUCHERINVENTORYENTRIES once verified against your data file.
"""

from datetime import date

from core.company_context import get_current_company_id
from storage.database import get_connection
from storage.repositories.voucher_repo import save_report_snapshot
from config.logging_config import get_logger

log = get_logger(__name__)


GST_VOUCHER_TYPES = (
    "Sales", "Purchase", "Credit Note", "Debit Note",
)


def generate_gst_summary(date_from=None, date_to=None):
    company_id = get_current_company_id()

    sql = """
        SELECT v.voucher_type, v.amount, v.party
        FROM vouchers v
        WHERE v.company_id = ?
    """
    params = [company_id]

    if date_from and date_to:
        sql += " AND v.voucher_date >= ? AND v.voucher_date <= ?"
        params.extend([date_from.strftime("%Y%m%d"), date_to.strftime("%Y%m%d")])

    sql += " AND v.voucher_type IN (?, ?, ?, ?)"
    params.extend(GST_VOUCHER_TYPES)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    summary = {vt: {"count": 0, "amount": 0.0} for vt in GST_VOUCHER_TYPES}
    for r in rows:
        vt = r["voucher_type"]
        summary[vt]["count"] += 1
        summary[vt]["amount"] += abs(r["amount"] or 0.0)

    result = {
        "company_id": company_id,
        "from": str(date_from or ""),
        "to": str(date_to or ""),
        "summary": summary,
        "total_vouchers": sum(s["count"] for s in summary.values()),
        "total_value": round(sum(s["amount"] for s in summary.values()), 2),
        "note": (
            "Rate-wise and HSN-wise breakdown requires the GST rate "
            "field from VoucherInventoryEntries. Extend extract_vouchers "
            "to include it before relying on this for return filing."
        ),
    }

    save_report_snapshot(
        company_id=company_id,
        report_type="gst_summary",
        result=result,
        params={"from": str(date_from), "to": str(date_to)},
    )
    return result
