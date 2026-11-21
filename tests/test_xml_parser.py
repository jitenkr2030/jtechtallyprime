"""Tests for the XML parser utilities."""

import unittest

from core.xml_parser import (
    parse_xml, local_name, get_field, get_name,
    count_elements, iter_elements,
)


class TestXmlParser(unittest.TestCase):

    SAMPLE_XML = (
        b"<ENVELOPE>"
        b"<LEDGER NAME='Cash' RESERVEDNAME=''>"
        b"<PARENT>Cash-in-Hand</PARENT>"
        b"<OPENINGBALANCE>5000</OPENINGBALANCE>"
        b"</LEDGER>"
        b"<LEDGER NAME='Bank A/C'>"
        b"<PARENT>Bank Accounts</PARENT>"
        b"<OPENINGBALANCE>-1200 Dr</OPENINGBALANCE>"
        b"</LEDGER>"
        b"</ENVELOPE>"
    )

    def setUp(self):
        self.root = parse_xml(self.SAMPLE_XML)

    def test_local_name(self):
        self.assertEqual(local_name("{ns}LEDGER"), "LEDGER")
        self.assertEqual(local_name("ledger"), "LEDGER")

    def test_get_field(self):
        ledgers = list(iter_elements(self.root, "LEDGER"))
        self.assertEqual(get_field(ledgers[0], "PARENT"), "Cash-in-Hand")
        self.assertEqual(get_field(ledgers[1], "PARENT"), "Bank Accounts")

    def test_get_name(self):
        ledgers = list(iter_elements(self.root, "LEDGER"))
        self.assertEqual(get_name(ledgers[0]), "Cash")
        self.assertEqual(get_name(ledgers[1]), "Bank A/C")

    def test_count_elements(self):
        self.assertEqual(count_elements(self.root, "LEDGER"), 2)
        self.assertEqual(count_elements(self.root, "GROUP"), 0)


if __name__ == "__main__":
    unittest.main()
