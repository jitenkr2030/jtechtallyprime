"""
JTech Tally Bridge - Voucher Type Master Reader
"""

import json

from config.settings import EXPORTS_DIR
from config.logging_config import get_logger
from core.tally_request import send_company_request, parse_tally_response
from core.xml_parser import get_field, get_name, iter_elements, count_elements
from core.sync_tracker import track_sync
from core.incremental_sync import master_altered_since
from storage.repositories.master_repo import save_voucher_types
from storage.repositories.voucher_repo import update_company_sync_timestamp

log = get_logger(__name__)


def _build_request(altered_since=None):
    sv_filter = f"<SVFROMDATE>{altered_since}</SVFROMDATE>" if altered_since else ""
    return f"""<ENVELOPE>
<HEADER>
<VERSION>1</VERSION>
<TALLYREQUEST>EXPORT</TALLYREQUEST>
<TYPE>COLLECTION</TYPE>
<ID>JTech Voucher Type Fields</ID>
</HEADER>
<BODY>
<DESC>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
{sv_filter}
</STATICVARIABLES>
<TDL>
<TDLMESSAGE>
<COLLECTION NAME="JTech Voucher Type Fields">
<TYPE>VoucherType</TYPE>
<FETCH>Name, Parent, IsDeemedPositive, NumberingMethod, IsReserved, UseForPOS, IsActive, Altertedon</FETCH>
</COLLECTION>
</TDLMESSAGE>
</TDL>
</DESC>
</BODY>
</ENVELOPE>"""


def extract_voucher_types(root):
    items = []

    for el in iter_elements(root, "VOUCHERTYPE"):
        name = get_name(el)
        if not name:
            continue

        items.append({
            "name": name,
            "reserved_name": el.attrib.get("RESERVEDNAME"),
            "parent": get_field(el, "PARENT"),
            "numbering_method": get_field(el, "NUMBERINGMETHOD"),
            "is_deemed_positive": get_field(el, "ISDEEMEDPOSITIVE"),
            "is_reserved": get_field(el, "ISRESERVED"),
            "is_active": get_field(el, "ISACTIVE"),
            "use_for_pos": get_field(el, "USEFORPOS"),
        })

    return items


@track_sync(sync_type="masters", reader_name="voucher_type_reader")
def read_voucher_types():
    log.info("Reading Voucher Type master from TallyPrime...")
    altered_since = master_altered_since()
    response, company = send_company_request(_build_request(altered_since))
    root, removed = parse_tally_response(response)

    items = extract_voucher_types(root)
    total = count_elements(root, "VOUCHERTYPE")

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORTS_DIR / f"voucher_types_company_{company['id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    saved = save_voucher_types(company["id"], items)
    update_company_sync_timestamp(company["id"], "masters")

    log.info(
        "Voucher Type master: company=%s http=%s elements=%d named=%d persisted=%d",
        company["id"], response.status_code,
        total, len(items), saved,
    )
    return items
