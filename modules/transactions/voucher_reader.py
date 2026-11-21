"""
JTech Tally Bridge - Voucher Reader (Phase 3 core)

Reads vouchers for a date range from TallyPrime, including:
- Header fields (type, number, date, party, narration, amount)
- GST header fields (party GSTIN, place of supply, registration type)
- Ledger allocations (every ledger debited/credited)
- Inventory allocations (stock items moved, HSN, GST rate, CGST/SGST/IGST)

Date range is paginated monthly to avoid Tally timeouts on
large datasets. When no `date_from` is supplied, the reader
defaults to `last_voucher_sync_at + 1 day` for incremental sync.
"""

import json
from datetime import date, timedelta

from config.settings import EXPORTS_DIR, DEFAULT_PAGE_DAYS
from config.logging_config import get_logger
from core.tally_request import send_company_request, parse_tally_response
from core.xml_parser import (
    get_field, get_name, iter_elements, count_elements,
)
from core.balance_parser import parse_balance
from core.company_context import get_current_company_id
from core.sync_tracker import track_sync
from core.incremental_sync import voucher_date_from_default, get_last_voucher_sync
from storage.repositories.voucher_repo import save_vouchers, update_company_sync_timestamp

log = get_logger(__name__)


def _build_request(date_from, date_to, voucher_type=None):
    sv_filter = f"""
    <SVFROMDATE>{date_from.strftime('%Y%m%d')}</SVFROMDATE>
    <SVTODATE>{date_to.strftime('%Y%m%d')}</SVTODATE>
    """
    type_filter = ""
    if voucher_type:
        type_filter = f"<SVVCHTYPE>{voucher_type}</SVVCHTYPE>"

    return f"""<ENVELOPE>
<HEADER>
<VERSION>1</VERSION>
<TALLYREQUEST>EXPORT</TALLYREQUEST>
<TYPE>COLLECTION</TYPE>
<ID>JTech Vouchers</ID>
</HEADER>
<BODY>
<DESC>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
{sv_filter}
{type_filter}
</STATICVARIABLES>
<TDL>
<TDLMESSAGE>
<COLLECTION NAME="JTech Vouchers" ISMODIFY="No" ISINITIALIZE="Yes">
<TYPE>Voucher</TYPE>
<FETCH>Date, TypeName, VoucherNumber, PartyLedgerName, PartyGSTIN,
PlaceOfSupply, Narration, LedgerEntries, AllInventoryEntries,
Amount, GUID, IsGSTApplicable, GSTRegistrationType</FETCH>
</COLLECTION>
</TDLMESSAGE>
</TDL>
</DESC>
</BODY>
</ENVELOPE>"""


def _parse_date(value):
    if not value:
        return None
    try:
        return value.strip()
    except AttributeError:
        return None


def _extract_ledger_allocations(voucher_el):
    """Pull every LEDGERENTRIES.* block from a voucher."""

    allocations = []

    for child in voucher_el:
        if child.tag.split("}")[-1].split(":")[-1].upper() != "LEDGERENTRIES":
            continue

        ledger = get_field(child, "LEDGERNAME") or child.attrib.get("LEDGERNAME")
        if not ledger:
            continue

        amount_raw = get_field(child, "AMOUNT")
        is_deemed = get_field(child, "ISDEEMEDPOSITIVE")

        allocations.append({
            "ledger": ledger.strip(),
            "group_name": get_field(child, "GROUP") or get_field(child, "PARENTLEDGERNAME"),
            "is_deemed_positive": is_deemed,
            "amount": parse_balance(amount_raw),
        })

    return allocations


def _extract_inventory_allocations(voucher_el):
    """Extract inventory lines including GST breakdown."""

    allocations = []

    for child in voucher_el:
        tag = child.tag.split("}")[-1].split(":")[-1].upper()
        if tag not in ("ALLINVENTORYENTRIES", "INVENTORYENTRIES"):
            continue

        stock_item = get_field(child, "STOCKITEMNAME") or child.attrib.get("STOCKITEMNAME")
        if not stock_item:
            continue

        # GST breakdown lives in nested LEDGERENTRIES inside each
        # inventory line, OR as direct fields depending on Tally
        # version. Try both.
        cgst = _sum_gst_suballoc(child, "CGST")
        sgst = _sum_gst_suballoc(child, "SGST")
        igst = _sum_gst_suballoc(child, "IGST")
        cess = _sum_gst_suballoc(child, "CESS")

        allocations.append({
            "stock_item": stock_item.strip(),
            "godown": get_field(child, "GODOWNNAME"),
            "qty": _parse_qty(get_field(child, "ACTUALQTY")),
            "rate": parse_balance(get_field(child, "RATE")),
            "amount": parse_balance(get_field(child, "AMOUNT")),
            "is_batch_wise": get_field(child, "ISBATCHWISEON"),
            "batch_name": get_field(child, "BATCHNAME"),
            "hsn_code": get_field(child, "HSNCODE"),
            "gst_rate": _parse_rate_percent(get_field(child, "GSTRATE")),
            "cgst_amount": cgst,
            "sgst_amount": sgst,
            "igst_amount": igst,
            "cess_amount": cess,
        })

    return allocations


def _sum_gst_suballoc(inv_el, gst_type):
    """
    Sum amounts from the nested ledger entries that post to a
    GST duty ledger (CGST/SGST/IGST/Cess). Tally puts these inside
    each inventory line as additional LEDGERENTRIES blocks with
    the duty ledger name.
    """

    total = 0.0
    found = False
    for child in inv_el:
        tag = child.tag.split("}")[-1].split(":")[-1].upper()
        if tag != "LEDGERENTRIES":
            continue
        ledger_name = (get_field(child, "LEDGERNAME") or "").upper()
        if gst_type.upper() in ledger_name:
            amount = parse_balance(get_field(child, "AMOUNT"))
            if amount:
                total += abs(amount)
                found = True
    return round(total, 2) if found else None


def _parse_qty(value):
    if not value:
        return None
    try:
        parts = str(value).strip().split()
        return float(parts[0])
    except (ValueError, IndexError):
        return None


def _parse_rate_percent(value):
    if not value:
        return None
    try:
        s = str(value).strip().rstrip("%").split("/")[0].strip()
        return float(s)
    except (ValueError, IndexError):
        return None


def extract_vouchers(root):
    vouchers = []

    for el in iter_elements(root, "VOUCHER"):
        voucher_type = get_field(el, "VOUCHERTYPENAME") or el.attrib.get("VCHTYPE")
        voucher_number = get_field(el, "VOUCHERNUMBER")

        if not voucher_type:
            continue

        date_str = get_field(el, "DATE")
        amount_raw = get_field(el, "AMOUNT")

        v = {
            "remote_id": el.attrib.get("REMOTEID") or el.attrib.get("MASTERID"),
            "voucher_type": voucher_type.strip(),
            "voucher_number": voucher_number,
            "voucher_date": _parse_date(date_str),
            "party": get_field(el, "PARTYLEDGERNAME"),
            "party_gstin": get_field(el, "PARTYGSTIN"),
            "place_of_supply": get_field(el, "PLACEOFSUPPLY"),
            "narration": get_field(el, "NARRATION"),
            "amount": parse_balance(amount_raw),
            "is_deemed_positive": get_field(el, "ISDEEMEDPOSITIVE"),
            "is_gst_applicable": get_field(el, "ISGSTAPPLICABLE"),
            "gst_registration_type": get_field(el, "GSTREGISTRATIONTYPE"),
            "guid": get_field(el, "GUID") or el.attrib.get("GUID"),
            "ledger_allocations": _extract_ledger_allocations(el),
            "inventory_allocations": _extract_inventory_allocations(el),
        }
        vouchers.append(v)

    return vouchers


def _month_chunks(date_from, date_to, days_per_chunk=DEFAULT_PAGE_DAYS):
    chunks = []
    start = date_from
    while start <= date_to:
        end = min(start + timedelta(days=days_per_chunk - 1), date_to)
        chunks.append((start, end))
        start = end + timedelta(days=1)
    return chunks


@track_sync(sync_type="vouchers", reader_name="voucher_reader")
def read_vouchers(date_from=None, date_to=None, voucher_type=None, persist=True):
    """
    Read vouchers between two dates (inclusive). Optionally filter
    by a specific voucher type name (e.g. 'Sales', 'Purchase').

    If `date_from` is None, defaults to `last_voucher_sync_at + 1 day`
    for incremental sync. If no prior sync exists, defaults to the
    start of the current financial year.
    """

    company_id = get_current_company_id()

    if date_from is None:
        date_from = voucher_date_from_default()
        log.info("Incremental sync: starting from %s", date_from)
    if date_to is None:
        date_to = date.today()

    all_vouchers = []

    for chunk_start, chunk_end in _month_chunks(date_from, date_to):
        log.info(
            "Reading vouchers: %s -> %s (type=%s)",
            chunk_start, chunk_end, voucher_type,
        )
        request_xml = _build_request(chunk_start, chunk_end, voucher_type)
        response, company = send_company_request(request_xml)
        root, _ = parse_tally_response(response)
        chunk_vouchers = extract_vouchers(root)
        all_vouchers.extend(chunk_vouchers)

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_{voucher_type.lower().replace(' ', '_')}" if voucher_type else ""
    json_path = EXPORTS_DIR / (
        f"vouchers_company_{company_id}{suffix}_"
        f"{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}.json"
    )
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_vouchers, f, indent=2, ensure_ascii=False, default=str)

    if persist:
        save_vouchers(company_id, all_vouchers)
        update_company_sync_timestamp(company_id, "vouchers")

    log.info(
        "Vouchers read: %d (persisted=%s) for company=%s",
        len(all_vouchers), persist, company_id,
    )
    return all_vouchers


def read_current_fy_vouchers():
    """Read vouchers for the current financial year (Apr 1 - Mar 31)."""

    today = date.today()
    if today.month >= 4:
        fy_start = date(today.year, 4, 1)
        fy_end = date(today.year + 1, 3, 31)
    else:
        fy_start = date(today.year - 1, 4, 1)
        fy_end = date(today.year, 3, 31)

    return read_vouchers(fy_start, fy_end)
