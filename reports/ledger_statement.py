"""
JTech Tally Bridge - Ledger Statement report

Per-ledger running statement: opening balance, every posting,
closing balance.
"""

from datetime import date

from core.company_context import get_current_company_id
from storage.database import get_connection
from storage.repositories.voucher_repo import save_report_snapshot
from reports.common import classify_group


def generate_ledger_statement(ledger_name, date_from, date_to):
    company_id = get_current_company_id()
    df_str = date_from.strftime("%Y%m%d")
    dt_str = date_to.strftime("%Y%m%d")

    with get_connection() as conn:
        ledger = conn.execute(
            "SELECT * FROM ledgers WHERE company_id = ? AND name = ? COLLATE NOCASE",
            (company_id, ledger_name),
        ).fetchone()

        if not ledger:
            raise ValueError(f"Ledger '{ledger_name}' not found in company {company_id}")

        opening = ledger["opening_balance_amount"] or 0.0
        group_name = ledger["parent_group"]
        classification = classify_group(group_name)

        lines = conn.execute(
            """
            SELECT v.voucher_date, v.voucher_type, v.voucher_number,
                   v.narration, vla.amount
            FROM voucher_ledger_allocations vla
            JOIN vouchers v ON v.id = vla.voucher_id
            WHERE v.company_id = ?
              AND vla.ledger = ? COLLATE NOCASE
              AND v.voucher_date >= ?
              AND v.voucher_date <= ?
            ORDER BY v.voucher_date, v.voucher_number
            """,
            (company_id, ledger_name, df_str, dt_str),
        ).fetchall()

    entries = []
    running = opening
    for ln in lines:
        amount = ln["amount"] or 0.0
        running += amount
        entries.append({
            "voucher_date": ln["voucher_date"],
            "voucher_type": ln["voucher_type"],
            "voucher_number": ln["voucher_number"],
            "narration": ln["narration"],
            "amount": round(amount, 2),
            "balance": round(running, 2),
        })

    closing = opening + sum(e["amount"] for e in entries)

    result = {
        "company_id": company_id,
        "ledger": ledger_name,
        "group": group_name,
        "classification": classification,
        "from": str(date_from),
        "to": str(date_to),
        "opening": round(opening, 2),
        "closing": round(closing, 2),
        "entries": entries,
        "entry_count": len(entries),
    }

    save_report_snapshot(
        company_id=company_id,
        report_type="ledger_statement",
        result=result,
        params={
            "ledger": ledger_name,
            "from": str(date_from),
            "to": str(date_to),
        },
    )
    return result
