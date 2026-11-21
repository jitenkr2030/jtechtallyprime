"""Tests for the balance parser."""

import unittest

from core.balance_parser import parse_balance


class TestBalanceParser(unittest.TestCase):

    def test_plain_number(self):
        self.assertEqual(parse_balance("5000"), 5000.0)

    def test_negative_number(self):
        self.assertEqual(parse_balance("-1200"), -1200.0)

    def test_indian_grouping(self):
        self.assertEqual(parse_balance("1,23,456.75"), 123456.75)

    def test_with_currency_prefix(self):
        self.assertEqual(parse_balance("Rs 50000.00"), 50000.0)

    def test_with_dr_indicator(self):
        self.assertEqual(parse_balance("5000 Dr"), 5000.0)

    def test_with_cr_indicator(self):
        self.assertEqual(parse_balance("5000 Cr"), -5000.0)

    def test_negative_with_dr(self):
        # Tally sometimes uses both
        self.assertEqual(parse_balance("-5000 Dr"), -5000.0)

    def test_empty_returns_none(self):
        self.assertIsNone(parse_balance(""))
        self.assertIsNone(parse_balance(None))
        self.assertIsNone(parse_balance("abc"))


if __name__ == "__main__":
    unittest.main()
