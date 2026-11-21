"""
JTech Tally Bridge - Sync tracking decorator

Wraps a reader function so that every call is recorded in the
sync_runs audit log automatically. Captures exceptions, counts,
and durations without the reader needing to know about sync_runs.

Usage:

    @track_sync(sync_type="masters", reader_name="ledger_reader")
    def read_ledgers(...):
        ...
        return ledgers

The decorated function must:
- Accept either no args or a first arg that yields a company_id
  via get_current_company_id()
- Return a list/iterable of records (used for count)
"""

import functools
import time
from datetime import datetime

from core.company_context import get_current_company_id, CompanyNotSelectedError
from storage.sync_runs import start_sync_run, complete_sync_run, fail_sync_run
from config.logging_config import get_logger

log = get_logger(__name__)


def track_sync(sync_type: str, reader_name: str, triggered_by: str = "cli"):
    """
    Decorator that wraps a reader call with sync_run audit logging.

    The decorated function's return value is treated as the records
    read; if it is a list, len() is used for records_read.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                company_id = get_current_company_id()
            except CompanyNotSelectedError:
                # Some readers (companies) don't need a selected company
                company_id = kwargs.get("company_id") or 0

            run = start_sync_run(
                company_id=company_id,
                sync_type=sync_type,
                reader_name=reader_name,
                triggered_by=triggered_by,
            )

            errors = []
            try:
                result = func(*args, **kwargs)
                records_read = 0
                if result is None:
                    records_read = 0
                elif isinstance(result, list):
                    records_read = len(result)
                elif isinstance(result, dict) and "records" in result:
                    records_read = len(result["records"])
                elif isinstance(result, dict):
                    # Single record
                    records_read = 1

                complete_sync_run(
                    run,
                    records_read=records_read,
                    records_persisted=records_read,
                    errors=errors,
                )
                return result
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
                fail_sync_run(run, errors)
                raise

        return wrapper

    return decorator
