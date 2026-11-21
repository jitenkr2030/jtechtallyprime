"""
JTech Tally Bridge - Balance Sheet report

Aggregates asset, liability, and equity ledger closing balances
as of a given date.
"""

from datetime import date
from typing import Optional

from reports.common import load_ledger_balances, get_company_id
from storage.repositories.voucher_repo import save_report_snapshot


def generate_balance_sheet(as_on=None):
    """Build a balance sheet snapshot."""

    company_id = get_company_id()
    # For balance sheet, "as on" = use closing balance of the period
    balances = load_ledger_balances(company_id, as_on, as_on)

    assets = []
    liabilities = []
    equity = []

    for name, info in sorted(balances.items()):
        closing = info["closing"]
        classification = info["classification"]

        if classification == "asset" and abs(closing) > 0.001:
            assets.append({
                "ledger": name,
                "group": info["group"],
                "amount": round(closing, 2),
            })
        elif classification == "liability" and closing < -0.001:
            liabilities.append({
                "ledger": name,
                "group": info["group"],
                "amount": round(-closing, 2),
            })
        elif classification == "equity" and closing < -0.001:
            equity.append({
                "ledger": name,
                "group": info["group"],
                "amount": round(-closing, 2),
            })

    assets_total = sum(a["amount"] for a in assets)
    liabilities_total = sum(l["amount"] for l in liabilities)
    equity_total = sum(e["amount"] for e in equity)

    result = {
        "company_id": company_id,
        "as_on": str(as_on or ""),
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "assets_total": round(assets_total, 2),
        "liabilities_total": round(liabilities_total, 2),
        "equity_total": round(equity_total, 2),
        "difference": round(assets_total - liabilities_total - equity_total, 2),
    }

    save_report_snapshot(
        company_id=company_id,
        report_type="balance_sheet",
        result=result,
        params={"as_on": str(as_on)},
    )
    return result
