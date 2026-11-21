"""
JTech Tally Bridge - Scheduler tasks

Defines the actual jobs that the scheduler runs.
"""

import time
from config.logging_config import get_logger

log = get_logger(__name__)


def sync_all_masters():
    """Pull all masters from Tally for the currently selected company."""

    from modules.ledger_reader import read_ledgers
    from modules.group_reader import read_groups
    from modules.voucher_type_reader import read_voucher_types
    from modules.stock_group_reader import read_stock_groups
    from modules.stock_item_reader import read_stock_items
    from modules.uom_reader import read_uoms
    from modules.cost_centre_reader import read_cost_centres
    from modules.cost_category_reader import read_cost_categories
    from modules.godown_reader import read_godowns

    for fn in (
        read_ledgers, read_groups, read_voucher_types,
        read_stock_groups, read_stock_items, read_uoms,
        read_cost_centres, read_cost_categories, read_godowns,
    ):
        try:
            fn()
        except Exception as exc:
            log.error("Scheduled master sync %s failed: %s", fn.__name__, exc)


def sync_current_fy_transactions():
    from modules.transactions.voucher_reader import read_current_fy_vouchers
    try:
        read_current_fy_vouchers()
    except Exception as exc:
        log.error("Scheduled transaction sync failed: %s", exc)


def schedule_master_sync(every_seconds=3600):
    """Schedule periodic master sync. Persists intent in app_settings."""

    from storage.database import get_connection
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value)
            VALUES ('master_sync_interval', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(every_seconds),),
        )
    log.info("Master sync scheduled every %ss", every_seconds)


def schedule_transaction_sync(every_seconds=86400):
    from storage.database import get_connection
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value)
            VALUES ('transaction_sync_interval', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(every_seconds),),
        )
    log.info("Transaction sync scheduled every %ss", every_seconds)


# Registry for the simple loop runner
TASKS = {
    "sync_masters": (sync_all_masters, 3600),
    "sync_transactions": (sync_current_fy_transactions, 86400),
}
