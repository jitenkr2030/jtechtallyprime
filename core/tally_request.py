"""
JTech Tally Bridge - Shared Tally Request Service

Centralizes company context, Tally HTTP requests,
XML sanitization and XML parsing.
"""

import xml.etree.ElementTree as ET

from core.connection import send_tally_request
from core.company_context import get_current_company
from core.xml_sanitizer import sanitize_xml
from core.xml_parser import parse_xml


def add_company_context(xml_request, company_name):
    """
    Add or update SVCurrentCompany in a Tally XML request.
    Does not modify the caller's original XML string.
    """

    try:
        root = ET.fromstring(xml_request)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid Tally request XML: {exc}") from exc

    static_variables = root.find(".//STATICVARIABLES")

    if static_variables is None:
        raise ValueError(
            "Tally request XML must contain STATICVARIABLES."
        )

    company_variable = static_variables.find("SVCurrentCompany")

    if company_variable is None:
        company_variable = ET.SubElement(
            static_variables,
            "SVCurrentCompany"
        )

    company_variable.text = company_name

    return ET.tostring(root, encoding="unicode")


def send_company_request(xml_request):
    """
    Send an XML request for the currently selected company.

    Returns:
        tuple: (HTTP response, selected company)
    """

    company = get_current_company()

    company_xml = add_company_context(
        xml_request,
        company["name"]
    )

    response = send_tally_request(company_xml)

    return response, company


def parse_tally_response(response):
    """
    Sanitize and parse a Tally HTTP response.

    Returns:
        tuple: (XML root, number of invalid references removed)
    """

    clean_xml, removed = sanitize_xml(response.content)

    root = parse_xml(clean_xml)

    return root, removed
