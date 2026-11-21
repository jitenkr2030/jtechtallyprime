"""
JTech Tally Bridge - Aging analysis (Debtors / Creditors)

For every ledger under Sundry Debtors / Sundry Creditors, computes
outstanding balance and buckets it by the age of the underlying
unreconciled invoice vouchers.

Buckets:
    0-30 days   (current)
    31-60 days
    61-90 days
    90+ days    (overdue)

Approach:
1. Identify party ledgers (parent_group == 'Sundry Debtors' /
   'Sundry Creditors').
2. For each party ledger, sum the voucher allocations where the
   ledger was debited (Dr = party owes us) or credited (Cr = we
   owe party) up to `as_on`.
3. The bucket boundaries are computed from the voucher_date of
   each allocation: age_days = (as_on - voucher_date).days
4. Each allocation's outstanding amount goes into the matching
   bucket.

This is a simplified aging: it does NOT net off payments against
specific invoices (FIFO matching). True BRS-level aging requires
bank allocation clearance dates, which the bridge does not yet
extract. Use this for indicative reporting.
"""

from datetime import date, datetime
from typing import Optional

from core.company_context import get_current_company_id
from storage.database import get_connection
from storage.repositories.voucher_repo import save_report_snapshot
from config.logging_config import get_logger

log = get_logger(__name__)


DEBTOR_GROUPS = ("Sundry Debtors",)
CREDITOR_GROUPS = ("Sundry Creditors",)

BUCKETS = [
    ("0-30", 0, 30),
    ("31-60", 31, 60),
    ("61-90", 61, 90),
    ("90+", 91, 99999),
]


def _normalize_date(d):
    if d is None:
        return date.today()
    if isinstance(d, date):
        return d
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def _date_to_int(d):
    """Convert a date or YYYYMMDD string to YYYYMMDD int for comparison."""

    if d is None:
        return None
    if isinstance(d, date):
        return int(d.strftime("%Y%m%d"))
    s = str(d).strip()
    try:
        return int(s)
    except ValueError:
        return None


def _bucket_for(age_days):
    for label, lo, hi in BUCKETS:
        if lo <= age_days <= hi:
            return label
    return "90+"


def _fetch_party_movements(company_id, as_on_int, parent_groups):
    """
    Return rows of (ledger, voucher_date, amount) for every allocation
    against a party ledger in the given parent groups, up to as_on.
    """

    placeholders = ",".join(["?"] * len(parent_groups))
    sql = f"""
        SELECT vla.ledger AS ledger,
               v.voucher_date AS voucher_date,
               vla.amount AS amount
        FROM voucher_ledger_allocations vla
        JOIN vouchers v ON v.id = vla.voucher_id
        JOIN ledgers l ON l.name = vla.ledger COLLATE NOCASE
                       AND l.company_id = v.company_id
        WHERE v.company_id = ?
          AND v.voucher_date <= ?
          AND l.parent_group IN ({placeholders})
        ORDER BY vla.ledger, v.voucher_date
    """
    params = [company_id, as_on_int, *parent_groups]

    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _fetch_party_opening_balances(company_id, parent_groups):
    """Return {ledger_name: opening_balance_amount}."""

    placeholders = ",".join(["?"] * len(parent_groups))
    sql = f"""
        SELECT name, opening_balance_amount
        FROM ledgers
        WHERE company_id = ?
          AND parent_group IN ({placeholders})
    """
    params = [company_id, *parent_groups]

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return {r["name"]: (r["opening_balance_amount"] or 0.0) for r in rows}


def _build_aging(as_on, parent_groups, sign, party_type):
    """sign = +1 for debtors (Dr outstanding = positive), -1 for creditors."""

    company_id = get_current_company_id()
    as_on_int = int(as_on.strftime("%Y%m%d"))

    openings = _fetch_party_opening_balances(company_id, parent_groups)
    movements = _fetch_party_movements(company_id, as_on_int, parent_groups)

    # Per-ledger aggregation
    ledger_rows = {}

    # Seed with opening balance - assumes opening is on the right side
    for ledger, opening in openings.items():
        ledger_rows[ledger] = {
            "ledger": ledger,
            "opening": round(opening * sign, 2),
            "buckets": {b[0]: 0.0 for b in BUCKETS},
            "total_outstanding": 0.0,
        }

    # Walk movements in date order, allocate each movement's absolute
    # amount to its age bucket. Sign convention: a Sales invoice debits
    # the debtor (positive amount) - this increases outstanding for
    # debtors. A Receipt credits the debtor (negative amount) - this
    # reduces outstanding. We sum amount * sign to get a signed
    # outstanding per movement, then bucket by absolute value.
    for mv in movements:
        ledger = mv["ledger"]
        if ledger not in ledger_rows:
            ledger_rows[ledger] = {
                "ledger": ledger,
                "opening": 0.0,
                "buckets": {b[0]: 0.0 for b in BUCKETS},
                "total_outstanding": 0.0,
            }

        vdate_str = mv["voucher_date"]
        try:
            vdate = datetime.strptime(str(vdate_str), "%Y%m%d").date()
        except ValueError:
            continue

        age_days = (as_on - vdate).days
        bucket = _bucket_for(max(age_days, 0))

        # Outstanding contribution of this movement.
        # For debtors: amount > 0 (Dr = invoice) increases outstanding.
        # For creditors: amount < 0 (Cr = invoice) increases outstanding
        # (we owe more).
        contribution = mv["amount"] * sign
        ledger_rows[ledger]["buckets"][bucket] += contribution

    # Total per ledger = opening + sum(buckets)
    rows = []
    for ledger, info in ledger_rows.items():
        bucket_sum = sum(info["buckets"].values())
        total = info["opening"] + bucket_sum
        info["buckets"] = {
            k: round(v, 2) for k, v in info["buckets"].items()
        }
        info["total_outstanding"] = round(total, 2)
        if abs(total) > 0.01:
            rows.append(info)

    rows.sort(key=lambda r: -abs(r["total_outstanding"]))

    bucket_totals = {b[0]: 0.0 for b in BUCKETS}
    for r in rows:
        for k, v in r["buckets"].items():
            bucket_totals[k] += v

    return {
        "rows": rows,
        "bucket_totals": {k: round(v, 2) for k, v in bucket_totals.items()},
        "grand_total": round(sum(r["total_outstanding"] for r in rows), 2),
    }


def generate_aging_report(as_on=None, party_type="both"):
    """
    Generate aging report for debtors and/or creditors.

    Args:
        as_on: cutoff date (default: today)
        party_type: 'debtors' / 'creditors' / 'both'

    Returns:
        {
            "company_id": int,
            "as_on": str,
            "debtors": {...} | None,
            "creditors": {...} | None,
        }
    """

    as_on = _normalize_date(as_on)
    company_id = get_current_company_id()

    result = {
        "company_id": company_id,
        "as_on": as_on.isoformat(),
        "party_type": party_type,
        "buckets": [b[0] for b in BUCKETS],
        "debtors": None,
        "creditors": None,
    }

    if party_type in ("debtors", "both"):
        result["debtors"] = _build_aging(
            as_on, DEBTOR_GROUPS, sign=+1, party_type="debtors",
        )
    if party_type in ("creditors", "both"):
        result["creditors"] = _build_aging(
            as_on, CREDITOR_GROUPS, sign=-1, party_type="creditors",
        )

    save_report_snapshot(
        company_id=company_id,
        report_type="aging",
        result=result,
        params={"as_on": as_on.isoformat(), "party_type": party_type},
    )
    return result
