"""
JTech Tally Bridge - Trial Balance report
"""

from datetime import date
from typing import Optional

from reports.common import load_ledger_balances, get_company_id
from storage.repositories.voucher_repo import save_report_snapshot


def generate_trial_balance(date_from=None, date_to=None):
    """
    Build a trial balance.

    Returns:
        {
            "company_id": int,
            "from": str, "to": str,
            "rows": [
                {"ledger": ..., "group": ..., "debit": ..., "credit": ...},
                ...
            ],
            "total_debit": float,
            "total_credit": float,
            "balanced": bool,
        }
    """

    company_id = get_company_id()
    balances = load_ledger_balances(company_id, date_from, date_to)

    rows = []
    total_debit = 0.0
    total_credit = 0.0

    for name, info in sorted(balances.items()):
        closing = info["closing"]
        if closing > 0.001:
            debit = round(closing, 2)
            credit = 0.0
            total_debit += debit
        elif closing < -0.001:
            debit = 0.0
            credit = round(-closing, 2)
            total_credit += credit
        else:
            debit = 0.0
            credit = 0.0

        rows.append({
            "ledger": name,
            "group": info["group"],
            "debit": debit,
            "credit": credit,
        })

    result = {
        "company_id": company_id,
        "from": str(date_from or ""),
        "to": str(date_to or ""),
        "rows": rows,
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "balanced": abs(total_debit - total_credit) < 0.01,
    }

    save_report_snapshot(
        company_id=company_id,
        report_type="trial_balance",
        result=result,
        params={"from": str(date_from), "to": str(date_to)},
    )
    return result
