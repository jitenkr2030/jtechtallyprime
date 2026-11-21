"""
Verify that TallyPrime returns ledger data
for the explicitly requested company.

Read-only diagnostic.
Does not modify existing exports.
"""

import xml.etree.ElementTree as ET

from modules.ledger_reader import REQUEST_XML
from storage.company_registry import list_companies
from core.connection import send_tally_request
from core.xml_sanitizer import sanitize_xml
from core.xml_parser import (
    parse_xml,
    extract_ledgers,
    count_ledger_elements,
)


def build_company_request(company_name):
    root = ET.fromstring(REQUEST_XML)

    static_variables = root.find(".//STATICVARIABLES")

    if static_variables is None:
        raise ValueError("STATICVARIABLES element not found.")

    company_variable = static_variables.find("SVCurrentCompany")

    if company_variable is None:
        company_variable = ET.SubElement(
            static_variables,
            "SVCurrentCompany"
        )

    company_variable.text = company_name

    return ET.tostring(root, encoding="unicode")


def test_company(company):
    request_xml = build_company_request(company["name"])

    response = send_tally_request(request_xml)

    clean_xml, removed = sanitize_xml(response.content)
    root = parse_xml(clean_xml)

    ledgers = extract_ledgers(root)
    total_elements = count_ledger_elements(root)

    return {
        "company_id": company["id"],
        "http_status": response.status_code,
        "ledger_elements": total_elements,
        "named_ledgers": len(ledgers),
        "invalid_references_removed": removed,
    }


def main():
    print("\nJTECH TALLY BRIDGE")
    print("COMPANY-SCOPED LEDGER DIAGNOSTIC")
    print("=" * 55)

    companies = list_companies()

    if not companies:
        print("No registered companies found.")
        return

    for company in companies:
        print(f"\nTesting registered Company ID: {company['id']}")

        result = test_company(company)

        print("HTTP status:", result["http_status"])
        print("Ledger XML elements:", result["ledger_elements"])
        print("Named ledgers:", result["named_ledgers"])
        print(
            "Invalid XML references removed:",
            result["invalid_references_removed"]
        )

    print("\nDiagnostic completed.")
    print("No ledger export file was modified.")


if __name__ == "__main__":
    main()
