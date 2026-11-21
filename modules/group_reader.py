"""
JTech Tally Bridge - Group Master Reader
"""

import json

from config.settings import EXPORTS_DIR
from config.logging_config import get_logger
from core.tally_request import send_company_request, parse_tally_response
from core.xml_parser import get_field, get_name, iter_elements, count_elements
from core.sync_tracker import track_sync
from core.incremental_sync import master_altered_since
from storage.repositories.master_repo import save_groups
from storage.repositories.voucher_repo import update_company_sync_timestamp

log = get_logger(__name__)


def _build_request(altered_since=None):
    sv_filter = f"<SVFROMDATE>{altered_since}</SVFROMDATE>" if altered_since else ""
    return f"""<ENVELOPE>
<HEADER>
<VERSION>1</VERSION>
<TALLYREQUEST>EXPORT</TALLYREQUEST>
<TYPE>COLLECTION</TYPE>
<ID>JTech Group Fields</ID>
</HEADER>
<BODY>
<DESC>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
{sv_filter}
</STATICVARIABLES>
<TDL>
<TDLMESSAGE>
<COLLECTION NAME="JTech Group Fields">
<TYPE>Group</TYPE>
<FETCH>Name, Parent, PrimaryGroup, IsRevenue, IsDeemedPositive, IsReserved, Altertedon</FETCH>
</COLLECTION>
</TDLMESSAGE>
</TDL>
</DESC>
</BODY>
</ENVELOPE>"""


def extract_groups(root):
    groups = []

    for element in iter_elements(root, "GROUP"):
        name = get_name(element)
        if not name:
            continue

        groups.append({
            "name": name,
            "reserved_name": element.attrib.get("RESERVEDNAME"),
            "parent": get_field(element, "PARENT"),
            "primary_group": get_field(element, "PRIMARYGROUP"),
            "is_revenue": get_field(element, "ISREVENUE"),
            "is_deemed_positive": get_field(element, "ISDEEMEDPOSITIVE"),
            "is_reserved": get_field(element, "ISRESERVED"),
        })

    return groups


def _export_path(company_id):
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORTS_DIR / f"groups_company_{company_id}.json"


@track_sync(sync_type="masters", reader_name="group_reader")
def read_groups():
    log.info("Reading Group master from TallyPrime...")
    altered_since = master_altered_since()
    response, company = send_company_request(_build_request(altered_since))
    root, removed = parse_tally_response(response)

    groups = extract_groups(root)
    total = count_elements(root, "GROUP")

    path = _export_path(company["id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(groups, f, indent=2, ensure_ascii=False)

    saved = save_groups(company["id"], groups)
    update_company_sync_timestamp(company["id"], "masters")

    log.info(
        "Group master: company=%s http=%s elements=%d named=%d persisted=%d removed_refs=%d",
        company["id"], response.status_code,
        total, len(groups), saved, removed,
    )
    return groups
