"""
JTech Tally Bridge - Company Reader

Read-only company discovery from TallyPrime.
"""

from core.connection import send_tally_request
from core.xml_sanitizer import sanitize_xml
from core.xml_parser import parse_xml, local_name, get_field


COMPANY_REQUEST_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>EXPORT</TALLYREQUEST>
        <TYPE>COLLECTION</TYPE>
        <ID>JTech Company List</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                <SVIsSimpleCompany>No</SVIsSimpleCompany>
            </STATICVARIABLES>
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION
                        NAME="JTech Company List"
                        ISMODIFY="No"
                        ISINITIALIZE="Yes">
                        <TYPE>Company</TYPE>
                        <NATIVEMETHOD>Name</NATIVEMETHOD>
                        <NATIVEMETHOD>StartingFrom</NATIVEMETHOD>
                        <NATIVEMETHOD>BooksFrom</NATIVEMETHOD>
                    </COLLECTION>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>
"""


def extract_companies(root):
    companies = []
    seen = set()

    for element in root.iter():
        if local_name(element.tag) != "COMPANY":
            continue

        name = (
            element.attrib.get("NAME")
            or get_field(element, "NAME")
        )

        if not name:
            continue

        name = name.strip()

        if not name or name.casefold() in seen:
            continue

        seen.add(name.casefold())

        companies.append({
            "name": name,
            "reserved_name": element.attrib.get("RESERVEDNAME"),
            "starting_from": get_field(element, "STARTINGFROM"),
            "books_from": get_field(element, "BOOKSFROM"),
        })

    return companies


def read_companies():
    response = send_tally_request(COMPANY_REQUEST_XML)
    clean_xml, removed = sanitize_xml(response.content)
    root = parse_xml(clean_xml)

    companies = extract_companies(root)

    return {
        "http_status": response.status_code,
        "invalid_references_removed": removed,
        "total_companies": len(companies),
        "companies": companies,
    }
