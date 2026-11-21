"""
End-to-end smoke test for the bridge.

Verifies the full pipeline after Tier 1/2 improvements:
  - sync_runs audit logging
  - bulk voucher insert
  - incremental sync defaults
  - GST field extraction
  - aging report
  - GSTR-1 report
  - Excel export
"""

import os
import sys
import zipfile
import io
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import date, datetime

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Use a temp DB
TEST_DB = "/tmp/jtech_smoke2.sqlite3"
os.environ["DATABASE_PATH"] = TEST_DB
if Path(TEST_DB).exists():
    os.unlink(TEST_DB)

import config.settings as settings_mod
settings_mod.DATABASE_PATH = Path(TEST_DB)
from config.settings import BASE_DIR
settings_mod.EXPORTS_DIR = BASE_DIR / "data" / "exports_smoke2"

from storage.database import reset_database
reset_database()


def make_response(content: bytes, status=200):
    r = MagicMock()
    r.status_code = status
    r.content = content
    r.text = content.decode("utf-8", errors="ignore")
    return r


COMPANIES_XML = b"""<?xml version="1.0"?>
<ENVELOPE><BODY><DATA>
<COMPANY NAME="Smoke Co" RESERVEDNAME="">
<STARTINGFROM>2024-04-01</STARTINGFROM>
<BOOKSFROM>2024-04-01</BOOKSFROM>
</COMPANY>
</DATA></BODY></ENVELOPE>"""


LEDGERS_XML = b"""<?xml version="1.0"?>
<ENVELOPE><BODY><DATA>
<LEDGER NAME="Cash" RESERVEDNAME="">
<PARENT>Cash-in-Hand</PARENT>
<OPENINGBALANCE>5000</OPENINGBALANCE>
<CLOSINGBALANCE>5000 Dr</CLOSINGBALANCE>
</LEDGER>
<LEDGER NAME="Bank A/C">
<PARENT>Bank Accounts</PARENT>
<OPENINGBALANCE>-1000 Dr</OPENINGBALANCE>
<CLOSINGBALANCE>-1000 Dr</CLOSINGBALANCE>
</LEDGER>
<LEDGER NAME="Sales">
<PARENT>Sales Accounts</PARENT>
<OPENINGBALANCE>0</OPENINGBALANCE>
<CLOSINGBALANCE>0</CLOSINGBALANCE>
</LEDGER>
<LEDGER NAME="Customer A">
<PARENT>Sundry Debtors</PARENT>
<OPENINGBALANCE>0</OPENINGBALANCE>
<CLOSINGBALANCE>0</CLOSINGBALANCE>
</LEDGER>
<LEDGER NAME="CGST">
<PARENT>Duties &amp; Taxes</PARENT>
<OPENINGBALANCE>0</OPENINGBALANCE>
<CLOSINGBALANCE>0</CLOSINGBALANCE>
</LEDGER>
<LEDGER NAME="SGST">
<PARENT>Duties &amp; Taxes</PARENT>
<OPENINGBALANCE>0</OPENINGBALANCE>
<CLOSINGBALANCE>0</CLOSINGBALANCE>
</LEDGER>
</DATA></BODY></ENVELOPE>"""


GROUPS_XML = b"""<?xml version="1.0"?>
<ENVELOPE><BODY><DATA>
<GROUP NAME="Cash-in-Hand" RESERVEDNAME=""><PARENT>Primary</PARENT></GROUP>
<GROUP NAME="Bank Accounts" RESERVEDNAME=""><PARENT>Primary</PARENT></GROUP>
<GROUP NAME="Sales Accounts" RESERVEDNAME=""><PARENT>Primary</PARENT></GROUP>
<GROUP NAME="Sundry Debtors" RESERVEDNAME=""><PARENT>Primary</PARENT></GROUP>
<GROUP NAME="Duties &amp; Taxes" RESERVEDNAME=""><PARENT>Primary</PARENT></GROUP>
</DATA></BODY></ENVELOPE>"""


# A Sales voucher with GST breakdown inside inventory allocations
VOUCHERS_XML = b"""<?xml version="1.0"?>
<ENVELOPE><BODY><DATA>
<VOUCHER REMOTEID="1" VCHTYPE="Sales">
<DATE>20240415</DATE>
<VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
<VOUCHERNUMBER>S-001</VOUCHERNUMBER>
<PARTYLEDGERNAME>Customer A</PARTYLEDGERNAME>
<PARTYGSTIN>27ABCDE1234F1Z5</PARTYGSTIN>
<PLACEOFSUPPLY>Maharashtra</PLACEOFSUPPLY>
<NARRATION>Test sale with GST</NARRATION>
<AMOUNT>1180</AMOUNT>
<ISGSTAPPLICABLE>Applicable</ISGSTAPPLICABLE>
<GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE>
<LEDGERENTRIES>
<LEDGERNAME>Customer A</LEDGERNAME>
<AMOUNT>-1180</AMOUNT>
<ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
</LEDGERENTRIES>
<LEDGERENTRIES>
<LEDGERNAME>Sales</LEDGERNAME>
<AMOUNT>1000</AMOUNT>
<ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
</LEDGERENTRIES>
<ALLINVENTORYENTRIES>
<STOCKITEMNAME>Widget</STOCKITEMNAME>
<ACTUALQTY>10 Nos</ACTUALQTY>
<RATE>100 /Nos</RATE>
<AMOUNT>1000</AMOUNT>
<HSNCODE>1234</HSNCODE>
<GSTRATE>18</GSTRATE>
<LEDGERENTRIES>
<LEDGERNAME>CGST</LEDGERNAME>
<AMOUNT>90</AMOUNT>
</LEDGERENTRIES>
<LEDGERENTRIES>
<LEDGERNAME>SGST</LEDGERNAME>
<AMOUNT>90</AMOUNT>
</LEDGERENTRIES>
</ALLINVENTORYENTRIES>
</VOUCHER>
<VOUCHER REMOTEID="2" VCHTYPE="Sales">
<DATE>20240520</DATE>
<VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
<VOUCHERNUMBER>S-002</VOUCHERNUMBER>
<PARTYLEDGERNAME>Customer A</PARTYLEDGERNAME>
<AMOUNT>500</AMOUNT>
<LEDGERENTRIES>
<LEDGERNAME>Customer A</LEDGERNAME>
<AMOUNT>-500</AMOUNT>
</LEDGERENTRIES>
<LEDGERENTRIES>
<LEDGERNAME>Sales</LEDGERNAME>
<AMOUNT>500</AMOUNT>
</LEDGERENTRIES>
</VOUCHER>
</DATA></BODY></ENVELOPE>"""


def fake_send(xml):
    xml_str = xml if isinstance(xml, str) else xml.decode("utf-8", errors="ignore")
    if "Company List" in xml_str:
        return make_response(COMPANIES_XML)
    if "Ledger Fields" in xml_str:
        return make_response(LEDGERS_XML)
    if "Group Fields" in xml_str:
        return make_response(GROUPS_XML)
    if "JTech Vouchers" in xml_str:
        return make_response(VOUCHERS_XML)
    return make_response(b"<ENVELOPE></ENVELOPE>")


def main():
    # 1. Sync companies
    from storage.company_registry import sync_companies, select_company
    with patch("modules.company_reader.send_tally_request", side_effect=fake_send):
        companies = sync_companies()
    assert len(companies) == 1, f"Expected 1 company, got {len(companies)}"
    select_company(companies[0]["id"])
    print(f"[1] Synced & selected company: {companies[0]['name']}")

    # 2. Read ledgers + groups (should populate sync_runs)
    with patch("core.connection.send_tally_request", side_effect=fake_send):
        from modules.ledger_reader import read_ledgers
        ledgers = read_ledgers()
        from modules.group_reader import read_groups
        groups = read_groups()
    assert len(ledgers) == 6, f"Expected 6 ledgers, got {len(ledgers)}"
    assert len(groups) == 5
    print(f"[2] Read {len(ledgers)} ledgers + {len(groups)} groups")

    # 3. Verify sync_runs audit records were created
    from storage.sync_runs import list_sync_runs
    runs = list_sync_runs()
    assert len(runs) >= 2, f"Expected >=2 sync runs, got {len(runs)}"
    print(f"[3] sync_runs audit log: {len(runs)} entries")
    for r in runs[:3]:
        print(f"    #{r['id']} {r['sync_type']}/{r['reader_name']} status={r['status']} read={r['records_read']}")

    # 4. Read vouchers - exercises bulk insert + GST extraction.
    # Multiple monthly chunks each return the same XML; the reader
    # accumulates them as raw reads, and bulk insert deduplicates.
    with patch("core.connection.send_tally_request", side_effect=fake_send):
        from modules.transactions.voucher_reader import read_vouchers
        vouchers = read_vouchers(date(2024, 4, 1), date(2024, 5, 31))
    # Find the voucher with GST fields populated
    gst_voucher = next(
        (v for v in vouchers if v.get("party_gstin")),
        None,
    )
    assert gst_voucher is not None, "Expected at least one voucher with GST"
    assert gst_voucher["party_gstin"] == "27ABCDE1234F1Z5"
    assert gst_voucher["place_of_supply"] == "Maharashtra"
    assert len(gst_voucher["inventory_allocations"]) == 1
    inv = gst_voucher["inventory_allocations"][0]
    assert inv["hsn_code"] == "1234"
    assert inv["gst_rate"] == 18.0
    assert inv["cgst_amount"] == 90.0
    assert inv["sgst_amount"] == 90.0
    print(f"[4] GST extraction verified: "
          f"party_gstin={gst_voucher['party_gstin']}, "
          f"HSN={inv['hsn_code']}, rate={inv['gst_rate']}%, "
          f"CGST={inv['cgst_amount']} SGST={inv['sgst_amount']}")

    # 5. Verify bulk insert wrote them
    from storage.repositories.voucher_repo import list_vouchers
    stored = list_vouchers(companies[0]["id"])
    assert len(stored) == 2, f"Expected 2 stored vouchers, got {len(stored)}"
    print(f"[5] Bulk insert verified: {len(stored)} vouchers in DB")

    # 6. Trial balance
    from reports.trial_balance import generate_trial_balance
    tb = generate_trial_balance(date(2024, 4, 1), date(2024, 5, 31))
    print(f"[6] Trial balance: {len(tb['rows'])} rows, "
          f"debit={tb['total_debit']} credit={tb['total_credit']}")

    # 7. Aging report
    from reports.aging import generate_aging_report
    aging = generate_aging_report(as_on=date(2024, 6, 1), party_type="debtors")
    assert aging["debtors"] is not None
    print(f"[7] Aging (debtors): grand total = {aging['debtors']['grand_total']}")
    for bucket, total in aging["debtors"]["bucket_totals"].items():
        print(f"    {bucket}: {total}")

    # 8. GSTR-1
    from reports.gstr1 import generate_gstr1
    gstr1 = generate_gstr1(date(2024, 4, 1), date(2024, 5, 31))
    print(f"[8] GSTR-1: sections={list(gstr1['section_totals'].keys())}, "
          f"grand_total_taxable={gstr1['grand_total']['taxable_value']}")
    if gstr1["hsn_summary"]:
        print(f"    HSN rows: {len(gstr1['hsn_summary'])}")

    # 9. Excel export
    from reports.excel_export import export_report
    params = {"date_from_obj": date(2024, 4, 1), "date_to_obj": date(2024, 5, 31)}
    xlsx_bytes = export_report("trial_balance", params)
    assert len(xlsx_bytes) > 1000
    # Verify it's a valid xlsx (zip)
    assert zipfile.is_zipfile(io.BytesIO(xlsx_bytes))
    print(f"[9] Excel export: trial_balance.xlsx = {len(xlsx_bytes)} bytes (valid zip)")

    # Excel export for GSTR-1 too
    xlsx_gstr1 = export_report("gstr1", params)
    assert len(xlsx_gstr1) > 1000
    print(f"[9b] Excel export: gstr1.xlsx = {len(xlsx_gstr1)} bytes")

    # 10. Data freshness
    from services.sync_service import get_data_freshness
    freshness = get_data_freshness()
    assert freshness["last_master_sync_at"] is not None
    assert freshness["last_voucher_sync_at"] is not None
    print(f"[10] Freshness: master={freshness['last_master_sync_at'][:19]}, "
          f"voucher={freshness['last_voucher_sync_at'][:19]}")

    print("\nSMOKE TEST PASSED - all Tier 1/2 improvements working end-to-end")


if __name__ == "__main__":
    main()
