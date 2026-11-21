"""
Tests for the company registry and master repositories.

Uses a temp DB so it does not pollute the user's real data file.
"""

import os
import unittest
from unittest.mock import patch

# Force a temp DB path before importing modules
os.environ.setdefault("DATABASE_PATH", "/tmp/jtech_test.sqlite3")

from storage.database import reset_database, get_connection
from storage.company_registry import (
    sync_companies, select_company, list_companies, get_selected_company,
)
from storage.repositories.master_repo import (
    save_ledgers, list_ledgers,
    save_groups, list_groups,
)


# Patch DATABASE_PATH
import config.settings as settings
settings.DATABASE_PATH = type(settings.Path())("/tmp/jtech_test.sqlite3")


def _fake_company_payload(*_args, **_kwargs):
    return {
        "http_status": 200,
        "invalid_references_removed": 0,
        "total_companies": 2,
        "companies": [
            {"name": "Test Co 1", "reserved_name": "",
             "starting_from": "2024-04-01", "books_from": "2024-04-01"},
            {"name": "Test Co 2", "reserved_name": "",
             "starting_from": "2024-04-01", "books_from": "2024-04-01"},
        ],
    }


class TestCompanyRegistry(unittest.TestCase):

    def setUp(self):
        reset_database()

    @patch("storage.company_registry.read_companies", side_effect=_fake_company_payload)
    def test_sync_and_select(self, _mock):
        companies = sync_companies()
        self.assertEqual(len(companies), 2)

        # Select first
        first = companies[0]
        select_company(first["id"])

        selected = get_selected_company()
        self.assertEqual(selected["name"], "Test Co 1")

    @patch("storage.company_registry.read_companies", side_effect=_fake_company_payload)
    def test_list_companies(self, _mock):
        sync_companies()
        companies = list_companies()
        self.assertEqual(len(companies), 2)


class TestMasterRepo(unittest.TestCase):

    def setUp(self):
        reset_database()
        # Manually insert a company
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO companies (name) VALUES (?)", ("Test Co",)
            )
            self.company_id = cur.lastrowid

    def test_save_and_list_ledgers(self):
        ledgers = [
            {"name": "Cash", "reserved_name": "", "group": "Cash-in-Hand",
             "opening_balance_raw": "5000", "opening_balance_amount": 5000.0,
             "closing_balance_raw": "5000", "closing_balance_amount": 5000.0},
            {"name": "Bank A/C", "reserved_name": "", "group": "Bank Accounts",
             "opening_balance_raw": "-1000 Dr", "opening_balance_amount": -1000.0,
             "closing_balance_raw": "-1000 Dr", "closing_balance_amount": -1000.0},
        ]
        saved = save_ledgers(self.company_id, ledgers)
        self.assertEqual(saved, 2)

        stored = list_ledgers(self.company_id)
        self.assertEqual(len(stored), 2)
        names = [l["name"] for l in stored]
        self.assertIn("Cash", names)
        self.assertIn("Bank A/C", names)

    def test_upsert_does_not_duplicate(self):
        # Save twice with same data - should not duplicate
        save_groups(self.company_id, [{"name": "Sales", "parent": "Primary"}])
        save_groups(self.company_id, [{"name": "Sales", "parent": "Primary"}])
        groups = list_groups(self.company_id)
        self.assertEqual(len(groups), 1)


if __name__ == "__main__":
    unittest.main()
