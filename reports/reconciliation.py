"""
JTech Tally Bridge - Data validation and reconciliation

Runs a battery of integrity checks against stored data and
returns categorized findings.
"""

from datetime import date

from core.company_context import get_current_company_id
from storage.database import get_connection
from config.logging_config import get_logger

log = get_logger(__name__)


def _check_ledger_group_resolution(company_id):
    """Ledgers whose parent group is missing from Group Master."""

    findings = []
    with get_connection() as conn:
        missing = conn.execute(
            """
            SELECT DISTINCT l.parent_group
            FROM ledgers l
            LEFT JOIN groups g
              ON g.company_id = l.company_id
             AND g.name = l.parent_group COLLATE NOCASE
            WHERE l.company_id = ?
              AND l.parent_group IS NOT NULL
              AND g.id IS NULL
            """,
            (company_id,),
        ).fetchall()

    for row in missing:
        findings.append(
            f"Group '{row['parent_group']}' referenced by ledgers but "
            f"absent in Group Master"
        )
    return findings


def _check_unbalanced_vouchers(company_id):
    """Vouchers whose ledger allocations do not net to zero."""

    findings = []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT v.id, v.voucher_type, v.voucher_number,
                   ROUND(SUM(vla.amount), 2) AS net
            FROM vouchers v
            JOIN voucher_ledger_allocations vla ON vla.voucher_id = v.id
            WHERE v.company_id = ?
            GROUP BY v.id
            HAVING ABS(net) > 0.01
            """,
            (company_id,),
        ).fetchall()

    for row in rows:
        findings.append(
            f"Voucher {row['voucher_type']} #{row['voucher_number']} "
            f"(id={row['id']}) net allocation = {row['net']} (should be 0)"
        )
    return findings


def _check_orphan_ledger_allocations(company_id):
    """Allocations referencing ledgers absent from master."""

    findings = []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT vla.ledger
            FROM voucher_ledger_allocations vla
            JOIN vouchers v ON v.id = vla.voucher_id
            LEFT JOIN ledgers l
              ON l.company_id = v.company_id
             AND l.name = vla.ledger COLLATE NOCASE
            WHERE v.company_id = ?
              AND l.id IS NULL
            """,
            (company_id,),
        ).fetchall()

    for row in rows:
        findings.append(
            f"Voucher allocation references ledger '{row['ledger']}' "
            f"which is not present in Ledger Master"
        )
    return findings


def _check_duplicate_vouchers(company_id):
    findings = []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT voucher_type, voucher_number, COUNT(*) AS cnt
            FROM vouchers
            WHERE company_id = ?
              AND voucher_number IS NOT NULL
            GROUP BY voucher_type, voucher_number
            HAVING cnt > 1
            """,
            (company_id,),
        ).fetchall()

    for row in rows:
        findings.append(
            f"Duplicate voucher: {row['voucher_type']} "
            f"#{row['voucher_number']} appears {row['cnt']} times"
        )
    return findings


def _check_trial_balance_dr_cr(company_id):
    """Trial balance totals should match."""

    from reports.trial_balance import generate_trial_balance
    tb = generate_trial_balance()
    if not tb["balanced"]:
        return [
            f"Trial balance not balanced: "
            f"debit={tb['total_debit']}, credit={tb['total_credit']}, "
            f"difference={round(tb['total_debit'] - tb['total_credit'], 2)}"
        ]
    return []


def run_full_reconciliation():
    company_id = get_current_company_id()

    results = {
        "company_id": company_id,
        "ledger_group_issues": _check_ledger_group_resolution(company_id),
        "unbalanced_vouchers": _check_unbalanced_vouchers(company_id),
        "orphan_ledger_allocations": _check_orphan_ledger_allocations(company_id),
        "duplicate_vouchers": _check_duplicate_vouchers(company_id),
        "trial_balance_check": _check_trial_balance_dr_cr(company_id),
    }

    results["passed"] = all(
        not v for k, v in results.items() if k != "passed" and k != "company_id"
    )

    log.info(
        "Reconciliation complete: passed=%s, issues=%d",
        results["passed"],
        sum(len(v) for k, v in results.items()
            if isinstance(v, list) and k not in ("company_id", "passed")),
    )
    return results
