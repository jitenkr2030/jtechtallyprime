"""
JTech Tally Bridge - Voucher type-specific readers

Each reader is a thin wrapper around voucher_reader.read_vouchers
that filters by a specific Tally voucher type. Tally's standard
voucher type names are used as filters.

Note: actual voucher type names in a given TallyPrime data file
may differ (user-defined sub-types under Sales / Purchase etc.).
Use `python main.py read-voucher-types` to list the names that
exist in the current company before relying on these filters.
"""

from datetime import date

from modules.transactions.voucher_reader import read_vouchers


def _fy_or_default(date_from, date_to):
    if date_from and date_to:
        return date_from, date_to
    today = date.today()
    if today.month >= 4:
        return date(today.year, 4, 1), date(today.year + 1, 3, 31)
    return date(today.year - 1, 4, 1), date(today.year, 3, 31)


def read_sales(date_from=None, date_to=None):
    df, dt = _fy_or_default(date_from, date_to)
    return read_vouchers(df, dt, voucher_type="Sales")


def read_purchases(date_from=None, date_to=None):
    df, dt = _fy_or_default(date_from, date_to)
    return read_vouchers(df, dt, voucher_type="Purchase")


def read_receipts(date_from=None, date_to=None):
    df, dt = _fy_or_default(date_from, date_to)
    return read_vouchers(df, dt, voucher_type="Receipt")


def read_payments(date_from=None, date_to=None):
    df, dt = _fy_or_default(date_from, date_to)
    return read_vouchers(df, dt, voucher_type="Payment")


def read_journals(date_from=None, date_to=None):
    df, dt = _fy_or_default(date_from, date_to)
    return read_vouchers(df, dt, voucher_type="Journal")


def read_credit_notes(date_from=None, date_to=None):
    df, dt = _fy_or_default(date_from, date_to)
    return read_vouchers(df, dt, voucher_type="Credit Note")


def read_debit_notes(date_from=None, date_to=None):
    df, dt = _fy_or_default(date_from, date_to)
    return read_vouchers(df, dt, voucher_type="Debit Note")


def read_inventory_transactions(date_from=None, date_to=None):
    """
    Read vouchers of types that affect inventory: Sales, Purchase,
    Credit Note, Debit Note, Delivery Note, Receipt Note, Stock Journal.
    Returns combined list. Useful for inventory reconciliation.
    """

    df, dt = _fy_or_default(date_from, date_to)
    combined = []
    for vtype in (
        "Sales", "Purchase",
        "Credit Note", "Debit Note",
        "Delivery Note", "Receipt Note",
        "Stock Journal", "Physical Stock",
    ):
        try:
            combined.extend(read_vouchers(df, dt, voucher_type=vtype))
        except Exception:
            # Not every company has every voucher type configured.
            pass
    return combined
