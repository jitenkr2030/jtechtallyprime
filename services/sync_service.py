"""
JTech Tally Bridge - Sync service

High-level operations:
- sync_all_masters(triggered_by)
- sync_vouchers(date_from, date_to, triggered_by)
- sync_everything(triggered_by)

Readers run in parallel threads (Tally itself is single-threaded
but parallel HTTP requests from our side are fine). Each reader
is wrapped by `track_sync`, so sync_runs records are populated
automatically.
"""

from datetime import date, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict

from config.logging_config import get_logger
from core.company_context import get_current_company, get_current_company_id
from storage.sync_runs import (
    list_sync_runs, get_sync_summary, get_last_successful,
)

log = get_logger(__name__)


MASTER_READERS = [
    ("ledger_reader", "modules.ledger_reader.read_ledgers"),
    ("group_reader", "modules.group_reader.read_groups"),
    ("voucher_type_reader", "modules.voucher_type_reader.read_voucher_types"),
    ("stock_group_reader", "modules.stock_group_reader.read_stock_groups"),
    ("stock_item_reader", "modules.stock_item_reader.read_stock_items"),
    ("uom_reader", "modules.uom_reader.read_uoms"),
    ("cost_centre_reader", "modules.cost_centre_reader.read_cost_centres"),
    ("cost_category_reader", "modules.cost_category_reader.read_cost_categories"),
    ("godown_reader", "modules.godown_reader.read_godowns"),
]


def _import_path(path):
    import importlib
    module_path, fn_name = path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, fn_name)


def sync_all_masters(triggered_by: str = "cli", parallel: bool = True) -> Dict:
    """
    Run every master reader for the currently selected company.

    Args:
        triggered_by: 'cli' / 'scheduler' / 'web'
        parallel: if True, run readers in parallel threads

    Returns:
        {
            "company_id": ...,
            "started_at": ...,
            "completed_at": ...,
            "results": {reader_name: {"records": N, "error": str?}, ...},
            "total_records": N,
            "errors": [...],
        }
    """

    company = get_current_company()
    company_id = company["id"]
    started_at = datetime.utcnow().isoformat()

    log.info(
        "sync_all_masters: company=%s triggered_by=%s parallel=%s",
        company_id, triggered_by, parallel,
    )

    results: Dict[str, Dict] = {}
    errors: List[str] = []

    if parallel:
        with ThreadPoolExecutor(max_workers=4) as pool:
            future_to_name = {
                pool.submit(_run_one, name, path, triggered_by): name
                for name, path in MASTER_READERS
            }
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    records, error = future.result()
                except Exception as exc:
                    records, error = 0, str(exc)
                results[name] = {"records": records, "error": error}
                if error:
                    errors.append(f"{name}: {error}")
    else:
        for name, path in MASTER_READERS:
            records, error = _run_one(name, path, triggered_by)
            results[name] = {"records": records, "error": error}
            if error:
                errors.append(f"{name}: {error}")

    completed_at = datetime.utcnow().isoformat()
    total_records = sum(r["records"] for r in results.values())

    log.info(
        "sync_all_masters complete: %d records, %d errors",
        total_records, len(errors),
    )

    return {
        "company_id": company_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "results": results,
        "total_records": total_records,
        "errors": errors,
    }


def _run_one(name, path, triggered_by):
    """Run one reader in isolation. Returns (records_count, error_or_None)."""

    try:
        fn = _import_path(path)
        # The reader is decorated with @track_sync which captures
        # triggered_by from its decorator. For now we accept that
        # the decorator's default 'cli' applies; advanced callers
        # can wrap the function with functools.partial.
        result = fn()
        if isinstance(result, list):
            return len(result), None
        if isinstance(result, dict):
            return len(result.get("records", [])) or 1, None
        return 0, None
    except Exception as exc:
        log.error("Reader %s failed: %s", name, exc, exc_info=True)
        return 0, str(exc)


def sync_vouchers(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    voucher_type: Optional[str] = None,
    triggered_by: str = "cli",
) -> Dict:
    """
    Pull vouchers for a date range. If date_from is None, the
    reader will use the incremental default (last_voucher_sync_at + 1).
    """

    from modules.transactions.voucher_reader import read_vouchers

    company_id = get_current_company_id()
    log.info(
        "sync_vouchers: company=%s from=%s to=%s type=%s by=%s",
        company_id, date_from, date_to, voucher_type, triggered_by,
    )

    vouchers = read_vouchers(
        date_from=date_from,
        date_to=date_to,
        voucher_type=voucher_type,
    )
    return {
        "company_id": company_id,
        "vouchers_read": len(vouchers),
        "from": str(date_from) if date_from else "incremental",
        "to": str(date_to) if date_to else str(date.today()),
    }


def sync_everything(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    triggered_by: str = "cli",
) -> Dict:
    """Run masters first, then vouchers for the given range."""

    masters_result = sync_all_masters(triggered_by=triggered_by)
    vouchers_result = sync_vouchers(
        date_from=date_from,
        date_to=date_to,
        triggered_by=triggered_by,
    )
    return {
        "masters": masters_result,
        "vouchers": vouchers_result,
    }


def get_sync_history(company_id: Optional[int] = None, limit: int = 50):
    return list_sync_runs(company_id=company_id, limit=limit)


def get_data_freshness(company_id: Optional[int] = None):
    """
    Return a freshness summary suitable for dashboard display:
        {
            "company_id": int,
            "company_name": str,
            "last_master_sync_at": str | None,
            "last_voucher_sync_at": str | None,
            "last_runs": [ ... recent sync_runs ... ],
        }
    """

    company = get_current_company()
    if company is None:
        return None

    cid = company_id or company["id"]
    last_runs = list_sync_runs(company_id=cid, limit=10)
    summary = get_sync_summary(company_id=cid)

    return {
        "company_id": cid,
        "company_name": company["name"],
        "last_master_sync_at": company.get("last_master_sync_at"),
        "last_voucher_sync_at": company.get("last_voucher_sync_at"),
        "last_runs": last_runs,
        "summary": summary,
    }
