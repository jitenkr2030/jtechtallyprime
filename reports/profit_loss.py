"""
JTech Tally Bridge - Profit & Loss report
"""

from datetime import date
from typing import Optional

from reports.common import load_ledger_balances, get_company_id
from storage.repositories.voucher_repo import save_report_snapshot


def generate_profit_loss(date_from=None, date_to=None):
    """
    Build a P&L statement by aggregating ledger movements for
    revenue and expense classifications.

    Returns:
        {
            "company_id": int,
            "from": ..., "to": ...,
            "income":  [ {ledger, amount, group}, ... ],
            "expenses": [ ... ],
            "income_total": float,
            "expense_total": float,
            "net_profit": float,
        }
    """

    company_id = get_company_id()
    balances = load_ledger_balances(company_id, date_from, date_to)

    income_rows = []
    expense_rows = []
    income_total = 0.0
    expense_total = 0.0

    for name, info in sorted(balances.items()):
        if info["classification"] == "revenue":
            # Credit balance = income; positive number = income
            amount = info["credit_movement"] - info["debit_movement"]
            income_rows.append({
                "ledger": name,
                "group": info["group"],
                "amount": round(amount, 2),
            })
            income_total += amount

        elif info["classification"] == "expense":
            amount = info["debit_movement"] - info["credit_movement"]
            expense_rows.append({
                "ledger": name,
                "group": info["group"],
                "amount": round(amount, 2),
            })
            expense_total += amount

    result = {
        "company_id": company_id,
        "from": str(date_from or ""),
        "to": str(date_to or ""),
        "income": income_rows,
        "expenses": expense_rows,
        "income_total": round(income_total, 2),
        "expense_total": round(expense_total, 2),
        "net_profit": round(income_total - expense_total, 2),
    }

    save_report_snapshot(
        company_id=company_id,
        report_type="profit_loss",
        result=result,
        params={"from": str(date_from), "to": str(date_to)},
    )
    return result
