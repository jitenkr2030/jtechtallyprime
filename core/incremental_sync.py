"""
JTech Tally Bridge - Incremental sync helpers

Reads `last_master_sync_at` / `last_voucher_sync_at` from the
companies table and uses them to scope the next pull:

- Masters: Tally supports an `ALTEREDON` field on most collections.
  We add `<SVFROMDATE>` to the STATICVARIABLES block of master
  requests when a previous sync exists.
- Vouchers: the existing date-range reader is already incremental
  by date. We default `date_from` to `last_voucher_sync_at + 1 day`
  when no explicit range is passed.

The first sync for a company always pulls everything (no last_sync_at).
"""

from datetime import datetime, timedelta
from typing import Optional

from storage.database import get_connection
from core.company_context import get_current_company_id


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except (ValueError, TypeError):
        return None


def get_last_master_sync(company_id: Optional[int] = None) -> Optional[datetime]:
    cid = company_id or get_current_company_id()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT last_master_sync_at FROM companies WHERE id = ?",
            (cid,),
        ).fetchone()
    if not row or not row["last_master_sync_at"]:
        return None
    try:
        return datetime.fromisoformat(row["last_master_sync_at"])
    except ValueError:
        return None


def get_last_voucher_sync(company_id: Optional[int] = None) -> Optional[datetime]:
    cid = company_id or get_current_company_id()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT last_voucher_sync_at FROM companies WHERE id = ?",
            (cid,),
        ).fetchone()
    if not row or not row["last_voucher_sync_at"]:
        return None
    try:
        return datetime.fromisoformat(row["last_voucher_sync_at"])
    except ValueError:
        return None


def master_altered_since() -> Optional[str]:
    """
    Return YYYYMMDD string to pass as <SVFROMDATE> for master
    collections, or None if no prior sync exists.
    """

    last = get_last_master_sync()
    if not last:
        return None
    # Incremental: pull records altered since the last sync + 1 day
    # to absorb any timezone drift.
    return (last + timedelta(days=1)).strftime("%Y%m%d")


def voucher_date_from_default():
    """
    Default 'from' date for voucher reads:
      - If we have a last_voucher_sync_at, use it + 1 day.
      - Otherwise, default to the start of the current financial year.
    """

    last = get_last_voucher_sync()
    if last:
        return (last + timedelta(days=1)).date()

    today = datetime.utcnow().date()
    if today.month >= 4:
        return today.replace(month=4, day=1)
    return today.replace(year=today.year - 1, month=4, day=1)
