"""
JTech Tally Bridge - Day Book report

Chronological list of vouchers in a date range with their
ledger allocations.
"""

from datetime import date

from core.company_context import get_current_company_id
from storage.database import get_connection
from storage.repositories.voucher_repo import save_report_snapshot


def generate_day_book(date_from, date_to):
    """List vouchers sorted by date and number."""

    company_id = get_current_company_id()
    df_str = date_from.strftime("%Y%m%d")
    dt_str = date_to.strftime("%Y%m%d")

    with get_connection() as conn:
        voucher_rows = conn.execute(
            """
            SELECT id, voucher_type, voucher_number, voucher_date,
                   party, narration, amount
            FROM vouchers
            WHERE company_id = ?
              AND voucher_date >= ?
              AND voucher_date <= ?
            ORDER BY voucher_date, voucher_number
            """,
            (company_id, df_str, dt_str),
        ).fetchall()

        vla_rows = conn.execute(
            """
            SELECT v.voucher_date, v.voucher_type, v.voucher_number,
                   vla.ledger, vla.amount
            FROM voucher_ledger_allocations vla
            JOIN vouchers v ON v.id = vla.voucher_id
            WHERE v.company_id = ?
              AND v.voucher_date >= ?
              AND v.voucher_date <= ?
            ORDER BY v.voucher_date, v.voucher_number
            """,
            (company_id, df_str, dt_str),
        ).fetchall()

    day_book = []
    for v in voucher_rows:
        day_book.append({
            "voucher_date": v["voucher_date"],
            "voucher_type": v["voucher_type"],
            "voucher_number": v["voucher_number"],
            "party": v["party"],
            "narration": v["narration"],
            "amount": v["amount"],
        })

    result = {
        "company_id": company_id,
        "from": str(date_from),
        "to": str(date_to),
        "vouchers": day_book,
        "ledger_lines": [dict(r) for r in vla_rows],
        "total_vouchers": len(day_book),
    }

    save_report_snapshot(
        company_id=company_id,
        report_type="day_book",
        result=result,
        params={"from": str(date_from), "to": str(date_to)},
    )
    return result
