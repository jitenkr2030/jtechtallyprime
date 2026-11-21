"""
JTech Tally Bridge - Bank Reconciliation (skeleton)

Identifies bank ledger entries that need reconciliation. A full BRS
requires the Bank Allocation block (BANKALLOCATIONS) from Tally with
cheque number, transaction date, clearance date, and value date.

This module currently surfaces unreconciled bank transactions from
stored data. To get clearance dates, extend `extract_vouchers` to
capture BANKALLOCATIONS, then refine this report.
"""

from datetime import date

from core.company_context import get_current_company_id
from storage.database import get_connection
from storage.repositories.voucher_repo import save_report_snapshot
from config.logging_config import get_logger

log = get_logger(__name__)


def _find_bank_ledgers(company_id):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT name FROM ledgers
            WHERE company_id = ?
              AND (parent_group = 'Bank Accounts'
                   OR parent_group LIKE '%Bank%'
                   OR name LIKE '%Bank%')
            """,
            (company_id,),
        ).fetchall()
    return [r["name"] for r in rows]


def generate_bank_reconciliation(as_on=None):
    company_id = get_current_company_id()
    banks = _find_bank_ledgers(company_id)

    if not banks:
        log.warning("No bank ledgers found for company %s", company_id)

    placeholders = ",".join(["?"] * len(banks)) if banks else "''"
    sql = f"""
        SELECT v.voucher_date, v.voucher_type, v.voucher_number,
               vla.ledger, vla.amount, v.narration
        FROM voucher_ledger_allocations vla
        JOIN vouchers v ON v.id = vla.voucher_id
        WHERE v.company_id = ?
          AND vla.ledger IN ({placeholders})
        ORDER BY v.voucher_date
    """
    params = [company_id] + banks

    if as_on:
        sql = sql.replace(
            "ORDER BY",
            f"AND v.voucher_date <= ? ORDER BY",
        )
        params.append(as_on.strftime("%Y%m%d"))

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    entries = []
    for r in rows:
        entries.append({
            "voucher_date": r["voucher_date"],
            "voucher_type": r["voucher_type"],
            "voucher_number": r["voucher_number"],
            "ledger": r["ledger"],
            "amount": r["amount"],
            "narration": r["narration"],
            "clearance_status": "UNKNOWN",
        })

    result = {
        "company_id": company_id,
        "as_on": str(as_on or ""),
        "bank_ledgers": banks,
        "entries": entries,
        "total_entries": len(entries),
        "note": (
            "Clearance status is 'UNKNOWN' until BANKALLOCATIONS are "
            "extracted from vouchers. Extend extract_vouchers to read "
            "the Bank Allocations block to enable full BRS."
        ),
    }

    save_report_snapshot(
        company_id=company_id,
        report_type="bank_reconciliation",
        result=result,
        params={"as_on": str(as_on)},
    )
    return result
