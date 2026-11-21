"""
JTech Tally Bridge - Base repository

Generic upsert/list helpers shared by all master repositories.
Each master table follows the same pattern:
  - one row per (company_id, name)
  - on conflict, update mutable fields and bump last_seen_at
"""

from typing import Iterable

from storage.database import get_connection


def upsert_many(
    table: str,
    columns: list,
    conflict_columns: list,
    update_columns: list,
    rows: Iterable[tuple],
):
    """
    Upsert multiple rows in one transaction.

    Args:
        table: target table name
        columns: full column list (in order)
        conflict_columns: columns in the UNIQUE constraint
        update_columns: mutable columns refreshed on conflict
        rows: iterable of tuples matching `columns` in order
    """

    if not rows:
        return 0

    placeholders = ", ".join(["?"] * len(columns))
    column_list = ", ".join(columns)

    set_clause = ", ".join(
        f"{col} = excluded.{col}" for col in update_columns
    ) + ", last_seen_at = CURRENT_TIMESTAMP"

    conflict_list = ", ".join(conflict_columns)

    sql = (
        f"INSERT INTO {table} ({column_list}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT({conflict_list}) DO UPDATE SET {set_clause}"
    )

    with get_connection() as conn:
        conn.executemany(sql, list(rows))

    return len(list(rows)) if hasattr(rows, "__len__") else 0


def list_for_company(table: str, company_id: int, order_by: str = "name"):
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE company_id = ? ORDER BY {order_by}",
            (company_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def find_one(table: str, company_id: int, name: str):
    with get_connection() as conn:
        row = conn.execute(
            f"SELECT * FROM {table} "
            f"WHERE company_id = ? AND name = ? COLLATE NOCASE",
            (company_id, name),
        ).fetchone()
    return dict(row) if row else None
