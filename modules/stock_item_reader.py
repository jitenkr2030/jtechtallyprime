"""
JTech Tally Bridge - Stock Item Master Reader
"""

import json

from config.settings import EXPORTS_DIR
from config.logging_config import get_logger
from core.tally_request import send_company_request, parse_tally_response
from core.xml_parser import get_field, get_name, iter_elements, count_elements
from core.balance_parser import parse_balance
from core.sync_tracker import track_sync
from core.incremental_sync import master_altered_since
from storage.repositories.master_repo import save_stock_items
from storage.repositories.voucher_repo import update_company_sync_timestamp

log = get_logger(__name__)


def _build_request(altered_since=None):
    sv_filter = f"<SVFROMDATE>{altered_since}</SVFROMDATE>" if altered_since else ""
    return f"""<ENVELOPE>
<HEADER>
<VERSION>1</VERSION>
<TALLYREQUEST>EXPORT</TALLYREQUEST>
<TYPE>COLLECTION</TYPE>
<ID>JTech Stock Item Fields</ID>
</HEADER>
<BODY>
<DESC>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
{sv_filter}
</STATICVARIABLES>
<TDL>
<TDLMESSAGE>
<COLLECTION NAME="JTech Stock Item Fields">
<TYPE>StockItem</TYPE>
<FETCH>Name, Parent, BaseUnits, OpeningBalance, ClosingBalance, RateOfGstCalculation, IsBatchWiseOn, HsnCode, GstRate, Altertedon</FETCH>
</COLLECTION>
</TDLMESSAGE>
</TDL>
</DESC>
</BODY>
</ENVELOPE>"""


def _parse_qty(value):
    if value is None:
        return None
    try:
        parts = str(value).strip().split()
        return float(parts[0])
    except (ValueError, IndexError):
        return None


def _parse_rate(value):
    if value is None:
        return None
    try:
        s = str(value).strip().rstrip("%").split("/")[0].strip()
        return float(s)
    except (ValueError, IndexError):
        return None


def extract_stock_items(root):
    items = []
    for el in iter_elements(root, "STOCKITEM"):
        name = get_name(el)
        if not name:
            continue

        opening_raw = get_field(el, "OPENINGBALANCE")
        closing_raw = get_field(el, "CLOSINGBALANCE")

        items.append({
            "name": name,
            "reserved_name": el.attrib.get("RESERVEDNAME"),
            "parent": get_field(el, "PARENT"),
            "uom": get_field(el, "BASEUNITS"),
            "opening_qty_raw": opening_raw,
            "opening_qty": _parse_qty(opening_raw),
            "opening_rate": None,
            "opening_value": parse_balance(opening_raw),
            "closing_qty": _parse_qty(closing_raw),
            "closing_value": parse_balance(closing_raw),
            "is_batch_wise": get_field(el, "ISBATCHWISEON"),
            "godown": get_field(el, "GODOWNNAME"),
            "hsn_code": get_field(el, "HSNCODE"),
            "gst_rate": _parse_rate(get_field(el, "GSTRATE")),
        })
    return items


@track_sync(sync_type="masters", reader_name="stock_item_reader")
def read_stock_items():
    log.info("Reading Stock Item master...")
    altered_since = master_altered_since()
    response, company = send_company_request(_build_request(altered_since))
    root, _ = parse_tally_response(response)

    items = extract_stock_items(root)
    total = count_elements(root, "STOCKITEM")

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORTS_DIR / f"stock_items_company_{company['id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    saved = save_stock_items(company["id"], items)
    update_company_sync_timestamp(company["id"], "masters")

    log.info(
        "Stock Item master: company=%s http=%s elements=%d named=%d persisted=%d",
        company["id"], response.status_code,
        total, len(items), saved,
    )
    return items
