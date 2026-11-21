"""
JTech Tally Bridge - Report service

Wraps report generation with:
- Optional caching via report_snapshots
- Excel export dispatch
- Parameter validation
"""

from datetime import date, datetime
from typing import Optional

from config.logging_config import get_logger
from core.company_context import get_current_company_id, get_current_company

log = get_logger(__name__)


def _parse(d):
    if not d:
        return None
    if isinstance(d, date):
        return d
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except ValueError:
        return None


def trial_balance(date_from=None, date_to=None):
    from reports.trial_balance import generate_trial_balance
    return generate_trial_balance(_parse(date_from), _parse(date_to))


def profit_loss(date_from=None, date_to=None):
    from reports.profit_loss import generate_profit_loss
    return generate_profit_loss(_parse(date_from), _parse(date_to))


def balance_sheet(as_on=None):
    from reports.balance_sheet import generate_balance_sheet
    return generate_balance_sheet(_parse(as_on))


def day_book(date_from, date_to):
    from reports.day_book import generate_day_book
    df, dt = _parse(date_from), _parse(date_to)
    if not (df and dt):
        raise ValueError("date_from and date_to required for day_book")
    return generate_day_book(df, dt)


def ledger_statement(ledger_name, date_from, date_to):
    from reports.ledger_statement import generate_ledger_statement
    df, dt = _parse(date_from), _parse(date_to)
    if not (df and dt):
        raise ValueError("date_from and date_to required")
    return generate_ledger_statement(ledger_name, df, dt)


def gst_summary(date_from=None, date_to=None):
    from reports.gst_reports import generate_gst_summary
    return generate_gst_summary(_parse(date_from), _parse(date_to))


def gstr1(date_from=None, date_to=None):
    from reports.gstr1 import generate_gstr1
    return generate_gstr1(_parse(date_from), _parse(date_to))


def gstr3b(date_from=None, date_to=None):
    from reports.gstr3b import generate_gstr3b
    return generate_gstr3b(_parse(date_from), _parse(date_to))


def bank_reconciliation(as_on=None):
    from reports.bank_reconciliation import generate_bank_reconciliation
    return generate_bank_reconciliation(_parse(as_on))


def aging_report(as_on=None, party_type="both"):
    from reports.aging import generate_aging_report
    return generate_aging_report(_parse(as_on), party_type=party_type)


def reconcile():
    from reports.reconciliation import run_full_reconciliation
    return run_full_reconciliation()


def export_excel(report_type, params):
    """
    Generate an Excel export of the named report.

    Returns: bytes (xlsx content)
    """

    from reports.excel_export import export_report
    return export_report(report_type, params)


def freshness():
    """Convenience wrapper around sync_service.get_data_freshness."""

    from services.sync_service import get_data_freshness
    return get_data_freshness()
