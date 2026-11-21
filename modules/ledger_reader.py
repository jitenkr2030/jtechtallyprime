"""
JTech Tally Bridge - Ledger Master Reader

Read-only ledger export for the currently selected company.
Persists results to SQLite AND writes a JSON export.

Incremental sync: when the company has a `last_master_sync_at`
value, the request is scoped to records altered since that date
via Tally's `ALTEREDON` collection filter. On the first sync,
all ledgers are pulled.
"""

import json

from config.settings import EXPORTS_DIR
from config.logging_config import get_logger
from core.tally_request import send_company_request, parse_tally_response
from core.xml_parser import get_field, get_name, iter_elements, count_elements
from core.balance_parser import parse_balance
from core.sync_tracker import track_sync
from core.incremental_sync import master_altered_since
from storage.repositories.master_repo import save_ledgers
from storage.repositories.voucher_repo import update_company_sync_timestamp
from storage.database import get_connection

log = get_logger(__name__)


def _build_request(altered_since=None):
    sv_filter = ""
    if altered_since:
        sv_filter = f"<SVFROMDATE>{altered_since}</SVFROMDATE>"

    return f"""<ENVELOPE>
<HEADER>
<VERSION>1</VERSION>
<TALLYREQUEST>EXPORT</TALLYREQUEST>
<TYPE>COLLECTION</TYPE>
<ID>JTech Ledger Fields</ID>
</HEADER>
<BODY>
<DESC>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
{sv_filter}
</STATICVARIABLES>
<TDL>
<TDLMESSAGE>
<COLLECTION NAME="JTech Ledger Fields">
<TYPE>Ledger</TYPE>
<FETCH>Name, Parent, OpeningBalance, ClosingBalance, Altertedon</FETCH>
</COLLECTION>
</TDLMESSAGE>
</TDL>
</DESC>
</BODY>
</ENVELOPE>"""


def extract_ledgers(root):
    """Extract ledger records from Tally XML."""

    ledgers = []

    for element in iter_elements(root, "LEDGER"):
        name = get_name(element)
        if not name:
            continue

        opening_raw = get_field(element, "OPENINGBALANCE")
        closing_raw = get_field(element, "CLOSINGBALANCE")

        ledgers.append({
            "name": name,
            "reserved_name": element.attrib.get("RESERVEDNAME"),
            "group": get_field(element, "PARENT"),
            "opening_balance_raw": opening_raw,
            "opening_balance_amount": parse_balance(opening_raw),
            "closing_balance_raw": closing_raw,
            "closing_balance_amount": parse_balance(closing_raw),
        })

    return ledgers


def _export_path(company_id):
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORTS_DIR / f"ledgers_company_{company_id}.json"


def _save_json(ledgers, company_id):
    path = _export_path(company_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ledgers, f, indent=2, ensure_ascii=False)
    return path


@track_sync(sync_type="masters", reader_name="ledger_reader")
def read_ledgers():
    log.info("Reading Ledger master from TallyPrime...")

    altered_since = master_altered_since()
    if altered_since:
        log.info("Incremental sync: pulling ledgers altered since %s", altered_since)
    else:
        log.info("Full sync: no last_master_sync_at, pulling all ledgers")

    request_xml = _build_request(altered_since)
    response, company = send_company_request(request_xml)
    root, removed = parse_tally_response(response)

    ledgers = extract_ledgers(root)
    total_elements = count_elements(root, "LEDGER")

    json_path = _save_json(ledgers, company["id"])
    saved = save_ledgers(company["id"], ledgers)

    update_company_sync_timestamp(company["id"], "masters")

    log.info(
        "Ledger master: company=%s http=%s xml_elements=%d named=%d persisted=%d removed_refs=%d",
        company["id"], response.status_code,
        total_elements, len(ledgers), saved, removed,
    )
    log.info("JSON exported: %s", json_path)
    return ledgers


def get_ledger_by_name(company_id, name):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM ledgers WHERE company_id = ? AND name = ? COLLATE NOCASE",
            (company_id, name),
        ).fetchone()
    return dict(row) if row else None
