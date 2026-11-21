"""Tests for the ledger extractor."""

import unittest

from modules.ledger_reader import extract_ledgers
from core.xml_parser import parse_xml


SAMPLE_LEDGER_XML = b"""<?xml version="1.0"?>
<ENVELOPE>
<BODY>
<DATA>
<LEDGER NAME="Cash" RESERVEDNAME="">
<PARENT>Cash-in-Hand</PARENT>
<OPENINGBALANCE>5000</OPENINGBALANCE>
<CLOSINGBALANCE>5000 Dr</CLOSINGBALANCE>
</LEDGER>
<LEDGER NAME="Bank A/C">
<PARENT>Bank Accounts</PARENT>
<OPENINGBALANCE>-1200 Dr</OPENINGBALANCE>
<CLOSINGBALANCE>-1200 Dr</CLOSINGBALANCE>
</LEDGER>
</DATA>
</BODY>
</ENVELOPE>"""


class TestLedgerReader(unittest.TestCase):

    def test_extract_ledgers(self):
        root = parse_xml(SAMPLE_LEDGER_XML)
        ledgers = extract_ledgers(root)
        self.assertEqual(len(ledgers), 2)
        self.assertEqual(ledgers[0]["name"], "Cash")
        self.assertEqual(ledgers[0]["group"], "Cash-in-Hand")
        self.assertEqual(ledgers[0]["opening_balance_amount"], 5000.0)
        self.assertEqual(ledgers[1]["name"], "Bank A/C")
        self.assertEqual(ledgers[1]["closing_balance_amount"], -1200.0)

    def test_skips_anonymous_ledgers(self):
        xml = b"<ENVELOPE><LEDGER><PARENT>X</PARENT></LEDGER></ENVELOPE>"
        root = parse_xml(xml)
        ledgers = extract_ledgers(root)
        self.assertEqual(ledgers, [])


if __name__ == "__main__":
    unittest.main()
