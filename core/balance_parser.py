"""
JTech Tally Bridge - Tally balance parser

TallyPrime returns balance values as strings such as:
    "Rs 50000.00"
    "-Rs 1200.00"
    "50000"
    "1,23,456.75 Dr"

This module converts them to signed floats suitable for
accounting calculations.
"""

import re
from decimal import Decimal, InvalidOperation

from config.logging_config import get_logger

log = get_logger(__name__)

_AMOUNT_RE = re.compile(
    r"""
    (?P<sign>-)?            # leading minus
    [^0-9]*                 # currency symbols, words like "Rs", "Dr"
    (?P<number>[0-9][0-9,]*\.?[0-9]*)
    (?:\s*(?P<dc>Dr|Cr))?   # trailing Dr/Cr indicator
    """,
    re.IGNORECASE | re.VERBOSE,
)


def parse_balance(raw):
    """
    Parse a Tally balance string into a signed float.

    Convention:
        Debit balances  -> positive
        Credit balances -> negative

    Returns:
        float: signed amount, or None if input cannot be parsed.
    """

    if raw is None:
        return None

    text = str(raw).strip()
    if not text:
        return None

    match = _AMOUNT_RE.search(text)
    if not match:
        log.debug("Unparseable balance value: %r", raw)
        return None

    number_str = match.group("number").replace(",", "").rstrip(".")

    try:
        amount = Decimal(number_str)
    except InvalidOperation:
        log.debug("Invalid numeric value in balance: %r", raw)
        return None

    # Tally sometimes encodes the sign both ways.
    # If an explicit leading '-' sign is present, it wins.
    # Otherwise apply Dr/Cr convention (Dr positive, Cr negative).
    if match.group("sign"):
        amount = -abs(amount)
    else:
        dc = (match.group("dc") or "").upper()
        if dc == "CR":
            amount = -abs(amount)
        elif dc == "DR":
            amount = abs(amount)

    return float(amount)


def balance_side(raw):
    """Return 'Dr', 'Cr' or None for a balance string."""

    if raw is None:
        return None
    text = str(raw)
    if "Dr" in text or "Dr" in text.title():
        if "-" in text or "Cr" in text.title():
            return "Cr" if "Cr" in text.title() else "Dr"
        return "Dr"
    if "Cr" in text.title():
        return "Cr"
    return None
