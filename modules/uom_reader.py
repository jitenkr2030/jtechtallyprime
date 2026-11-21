"""
JTech Tally Bridge - Unit of Measurement (UOM) Reader
"""

import json

from config.settings import EXPORTS_DIR
from config.logging_config import get_logger
from core.tally_request import send_company_request, parse_tally_response
from core.xml_parser import get_field, get_name, iter_elements, count_elements
from core.sync_tracker import track_sync
from core.incremental_sync import master_altered_since
from storage.repositories.master_repo import save_units
from storage.repositories.voucher_repo import update_company_sync_timestamp

log = get_logger(__name__)


def _build_request(altered_since=None):
    sv_filter = f"<SVFROMDATE>{altered_since}</SVFROMDATE>" if altered_since else ""
    return f"""<ENVELOPE>
<HEADER>
<VERSION>1</VERSION>
<TALLYREQUEST>EXPORT</TALLYREQUEST>
<TYPE>COLLECTION</TYPE>
<ID>JTech Unit Fields</ID>
</HEADER>
<BODY>
<DESC>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
{sv_filter}
</STATICVARIABLES>
<TDL>
<TDLMESSAGE>
<COLLECTION NAME="JTech Unit Fields">
<TYPE>Unit</TYPE>
<FETCH>Name, DecimalPlaces, Altertedon</FETCH>
</COLLECTION>
</TDLMESSAGE>
</TDL>
</DESC>
</BODY>
</ENVELOPE>"""


def _int(value):
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def extract_units(root):
    items = []
    for el in iter_elements(root, "UNIT"):
        name = get_name(el)
        if not name:
            continue
        items.append({
            "name": name,
            "reserved_name": el.attrib.get("RESERVEDNAME"),
            "decimal_places": _int(get_field(el, "DECIMALPLACES")),
        })
    return items


@track_sync(sync_type="masters", reader_name="uom_reader")
def read_uoms():
    log.info("Reading Unit master...")
    altered_since = master_altered_since()
    response, company = send_company_request(_build_request(altered_since))
    root, _ = parse_tally_response(response)

    items = extract_units(root)
    total = count_elements(root, "UNIT")

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORTS_DIR / f"units_company_{company['id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    saved = save_units(company["id"], items)
    update_company_sync_timestamp(company["id"], "masters")

    log.info(
        "Unit master: company=%s http=%s elements=%d named=%d persisted=%d",
        company["id"], response.status_code,
        total, len(items), saved,
    )
    return items
