"""
JTech Tally Bridge - Sync runs audit log

Every import (masters, vouchers, reconciliation) is wrapped in a
sync run record so the user can answer "when was data last
refreshed, and how many records came through?".

Usage pattern (readers call this):

    run = start_sync_run(company_id, "masters", "ledger_reader")
    try:
        ...
        complete_sync_run(run, records_read=N, records_persisted=M)
    except Exception as exc:
        fail_sync_run(run, errors=[str(exc)])
        raise
"""

import json
import time
from datetime import datetime
from typing import Optional, List

from storage.database import get_connection
from config.logging_config import get_logger

log = get_logger(__name__)


def start_sync_run(
    company_id: int,
    sync_type: str,
    reader_name: Optional[str] = None,
    triggered_by: str = "cli",
):
    """
    Create a sync_run record at the start of an import.

    Returns:
        dict with at least `id` and `started_at` for the caller to
        pass back to `complete_sync_run` / `fail_sync_run`.
    """

    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO sync_runs
            (company_id, sync_type, reader_name, started_at,
             triggered_by, status)
            VALUES (?, ?, ?, ?, ?, 'running')
            """,
            (
                company_id,
                sync_type,
                reader_name,
                datetime.utcnow().isoformat(),
                triggered_by,
            ),
        )
        run_id = cur.lastrowid

    log.info(
        "Sync run #%d started: company=%s type=%s reader=%s by=%s",
        run_id, company_id, sync_type, reader_name, triggered_by,
    )
    return {
        "id": run_id,
        "company_id": company_id,
        "sync_type": sync_type,
        "reader_name": reader_name,
        "started_at": datetime.utcnow().isoformat(),
        "_t0": time.time(),
    }


def complete_sync_run(
    run,
    records_read: int = 0,
    records_persisted: int = 0,
    errors: Optional[List[str]] = None,
):
    """Mark a sync run as completed and record counts."""

    duration = time.time() - run.get("_t0", time.time())
    errors = errors or []
    completed_at = datetime.utcnow().isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE sync_runs SET
                completed_at = ?,
                records_read = ?,
                records_persisted = ?,
                errors_count = ?,
                error_details_json = ?,
                duration_seconds = ?,
                status = ?
            WHERE id = ?
            """,
            (
                completed_at,
                records_read,
                records_persisted,
                len(errors),
                json.dumps(errors) if errors else None,
                round(duration, 3),
                "completed" if not errors else "completed_with_errors",
                run["id"],
            ),
        )

    log.info(
        "Sync run #%d completed in %.2fs: read=%d persisted=%d errors=%d",
        run["id"], duration, records_read, records_persisted, len(errors),
    )


def fail_sync_run(run, errors: List[str]):
    """Mark a sync run as failed with error details."""

    duration = time.time() - run.get("_t0", time.time())
    completed_at = datetime.utcnow().isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE sync_runs SET
                completed_at = ?,
                errors_count = ?,
                error_details_json = ?,
                duration_seconds = ?,
                status = 'failed'
            WHERE id = ?
            """,
            (
                completed_at,
                len(errors),
                json.dumps(errors),
                round(duration, 3),
                run["id"],
            ),
        )

    log.error(
        "Sync run #%d failed after %.2fs: %s",
        run["id"], duration, errors,
    )


def list_sync_runs(company_id: Optional[int] = None, limit: int = 50):
    """List recent sync runs, newest first."""

    sql = """
        SELECT sr.*, c.name AS company_name
        FROM sync_runs sr
        JOIN companies c ON c.id = sr.company_id
    """
    params = []
    if company_id:
        sql += " WHERE sr.company_id = ?"
        params.append(company_id)
    sql += " ORDER BY sr.started_at DESC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_sync_run(run_id: int):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT sr.*, c.name AS company_name
            FROM sync_runs sr
            JOIN companies c ON c.id = sr.company_id
            WHERE sr.id = ?
            """,
            (run_id,),
        ).fetchone()
    return dict(row) if row else None


def get_last_successful(company_id: int, sync_type: str):
    """Return the most recent completed sync run of given type."""

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM sync_runs
            WHERE company_id = ?
              AND sync_type = ?
              AND status IN ('completed', 'completed_with_errors')
            ORDER BY completed_at DESC
            LIMIT 1
            """,
            (company_id, sync_type),
        ).fetchone()
    return dict(row) if row else None


def get_sync_summary(company_id: Optional[int] = None):
    """Return per-(company, sync_type) summary of last runs."""

    sql = """
        SELECT company_id,
               sync_type,
               MAX(completed_at) AS last_run_at,
               SUM(records_read) AS total_records_read,
               SUM(records_persisted) AS total_records_persisted,
               SUM(errors_count) AS total_errors,
               COUNT(*) AS run_count
        FROM sync_runs
        WHERE status IN ('completed', 'completed_with_errors')
    """
    params = []
    if company_id:
        sql += " AND company_id = ?"
        params.append(company_id)
    sql += " GROUP BY company_id, sync_type"

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
