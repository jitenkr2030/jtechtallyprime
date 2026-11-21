"""
JTech Tally Bridge - Common report utilities

Shared helpers for:
- Loading ledgers + voucher allocations from SQLite for a period
- Building opening / movement / closing balance tables per ledger
- Group classification (revenue/asset/liability/equity) using
  is_revenue and is_deemed_positive flags on the Group master.
"""

from datetime import date
from typing import Optional

from core.company_context import get_current_company_id
from storage.database import get_connection
from config.logging_config import get_logger

log = get_logger(__name__)


# Tally's standard primary groups. These names come directly from
# Tally's Group Master export and should not be translated.
PRIMARY_REVENUE_GROUPS = {
    "Direct Income", "Indirect Income",
    "Sales Accounts", "Purchase Accounts",
    "Other Income",
}
PRIMARY_EXPENSE_GROUPS = {
    "Direct Expenses", "Indirect Expenses",
    "Purch. Expenses", "Selling Expenses",
}
PRIMARY_ASSET_GROUPS = {
    "Fixed Assets", "Current Assets",
    "Sundry Debtors", "Cash-in-Hand", "Bank Accounts",
    "Stock-in-Hand", "Loans & Advances (Asset)",
    "Investments", "Misc. Expenses (Asset)",
}
PRIMARY_LIABILITY_GROUPS = {
    "Sundry Creditors", "Loans (Liability)",
    "Duties & Taxes", "Provisions",
    "Current Liabilities", "Capital Account",
    "Reserves & Surplus",
}


def classify_group(group):
    """Classify a group into one of: revenue, expense, asset, liability, equity."""

    g = (group or "").strip()

    if g in PRIMARY_REVENUE_GROUPS:
        return "revenue"
    if g in PRIMARY_EXPENSE_GROUPS:
        return "expense"
    if g in PRIMARY_ASSET_GROUPS:
        return "asset"
    if g in PRIMARY_LIABILITY_GROUPS:
        return "liability" if g != "Capital Account" else "equity"
    if g.lower() in ("capital account",):
        return "equity"
    if g.lower() in ("reserves & surplus",):
        return "equity"
    return "other"


def _default_period(date_from, date_to):
    if date_from and date_to:
        return date_from, date_to
    today = date.today()
    if today.month >= 4:
        return date(today.year, 4, 1), date(today.year + 1, 3, 31)
    return date(today.year - 1, 4, 1), date(today.year, 3, 31)


def load_ledger_balances(company_id, date_from=None, date_to=None):
    """
    Return a dict keyed by ledger name with structure:
        {
            name: {
                "group": str,
                "classification": revenue/expense/asset/...,
                "opening": float (from master),
                "debit_movement": float,
                "credit_movement": float,
                "closing": float (computed),
            }
        }
    """

    date_from, date_to = _default_period(date_from, date_to)
    df_str = date_from.strftime("%Y%m%d")
    dt_str = date_to.strftime("%Y%m%d")

    with get_connection() as conn:
        ledgers = {
            row["name"]: {
                "group": row["parent_group"],
                "classification": classify_group(row["parent_group"]),
                "opening": row["opening_balance_amount"] or 0.0,
                "debit_movement": 0.0,
                "credit_movement": 0.0,
                "closing": row["closing_balance_amount"] or 0.0,
            }
            for row in conn.execute(
                "SELECT name, parent_group, opening_balance_amount, "
                "closing_balance_amount FROM ledgers WHERE company_id = ?",
                (company_id,),
            ).fetchall()
        }

        # movements from vouchers
        movements = conn.execute(
            """
            SELECT vla.ledger AS ledger,
                   SUM(CASE WHEN vla.amount > 0 THEN vla.amount ELSE 0 END) AS debit,
                   SUM(CASE WHEN vla.amount < 0 THEN -vla.amount ELSE 0 END) AS credit
            FROM voucher_ledger_allocations vla
            JOIN vouchers v ON v.id = vla.voucher_id
            WHERE v.company_id = ?
              AND v.voucher_date >= ?
              AND v.voucher_date <= ?
            GROUP BY vla.ledger
            """,
            (company_id, df_str, dt_str),
        ).fetchall()

    for mv in movements:
        ledger_name = mv["ledger"]
        if ledger_name not in ledgers:
            # Ledger might not yet be in master (rare) - create stub
            ledgers[ledger_name] = {
                "group": None,
                "classification": "other",
                "opening": 0.0,
                "debit_movement": 0.0,
                "credit_movement": 0.0,
                "closing": 0.0,
            }
        ledgers[ledger_name]["debit_movement"] += mv["debit"] or 0.0
        ledgers[ledger_name]["credit_movement"] += mv["credit"] or 0.0

    # Recompute closing for ledgers where we have movements
    # (closing = opening + debit_movement - credit_movement for asset/expense
    #  and  opening + credit_movement - debit_movement for liability/revenue/equity)
    for name, info in ledgers.items():
        classification = info["classification"]
        if classification in ("asset", "expense"):
            info["closing"] = (
                info["opening"] + info["debit_movement"] - info["credit_movement"]
            )
        elif classification in ("liability", "revenue", "equity"):
            info["closing"] = (
                info["opening"] + info["credit_movement"] - info["debit_movement"]
            )
        else:
            # Unknown - net
            info["closing"] = (
                info["opening"] + info["debit_movement"] - info["credit_movement"]
            )

    return ledgers


def get_company_id():
    return get_current_company_id()
