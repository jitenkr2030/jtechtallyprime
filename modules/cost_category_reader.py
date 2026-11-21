"""
JTech Tally Bridge - Cost Category Reader
"""

import json

from config.settings import EXPORTS_DIR
from config.logging_config import get_logger
from core.tally_request import send_company_request, parse_tally_response
from core.xml_parser import get_name, iter_elements, count_elements
from core.sync_tracker import track_sync
from core.incremental_sync import master_altered_since
from storage.repositories.master_repo import save_cost_categories
from storage.repositories.voucher_repo import update_company_sync_timestamp

log = get_logger(__name__)


def _build_request(altered_since=None):
    sv_filter = f"<SVFROMDATE>{altered_since}</SVFROMDATE>" if altered_since else ""
    return f"""<ENVELOPE>
<HEADER>
<VERSION>1</VERSION>
<TALLYREQUEST>EXPORT</TALLYREQUEST>
<TYPE>COLLECTION</TYPE>
<ID>JTech Cost Category Fields</ID>
</HEADER>
<BODY>
<DESC>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
{sv_filter}
</STATICVARIABLES>
<TDL>
<TDLMESSAGE>
<COLLECTION NAME="JTech Cost Category Fields">
<TYPE>CostCategory</TYPE>
<FETCH>Name, Altertedon</FETCH>
</COLLECTION>
</TDLMESSAGE>
</TDL>
</DESC>
</BODY>
</ENVELOPE>"""


def extract_cost_categories(root):
    items = []
    for el in iter_elements(root, "COSTCATEGORY"):
        name = get_name(el)
        if not name:
            continue
        items.append({
            "name": name,
            "reserved_name": el.attrib.get("RESERVEDNAME"),
        })
    return items


@track_sync(sync_type="masters", reader_name="cost_category_reader")
def read_cost_categories():
    log.info("Reading Cost Category master...")
    altered_since = master_altered_since()
    response, company = send_company_request(_build_request(altered_since))
    root, _ = parse_tally_response(response)

    items = extract_cost_categories(root)
    total = count_elements(root, "COSTCATEGORY")

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORTS_DIR / f"cost_categories_company_{company['id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    saved = save_cost_categories(company["id"], items)
    update_company_sync_timestamp(company["id"], "masters")

    log.info(
        "Cost Category master: company=%s http=%s elements=%d named=%d persisted=%d",
        company["id"], response.status_code,
        total, len(items), saved,
    )
    return items
