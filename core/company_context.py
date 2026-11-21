"""
JTech Tally Bridge - Shared Company Context

Provides the explicitly selected Tally company to all modules.
"""

from storage.company_registry import get_selected_company


class CompanyNotSelectedError(Exception):
    """Raised when an accounting operation has no selected company."""


def get_current_company():
    """
    Return the currently selected company.

    Returns:
        dict: Selected company record.
    """

    company = get_selected_company()

    if company is None:
        raise CompanyNotSelectedError(
            "No company selected. Select a company before continuing."
        )

    if not company.get("id") or not company.get("name"):
        raise CompanyNotSelectedError(
            "Selected company record is incomplete. Sync companies again."
        )

    return company


def get_current_company_id():
    return get_current_company()["id"]


def get_current_company_name():
    return get_current_company()["name"]
