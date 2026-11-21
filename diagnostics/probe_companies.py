from core.connection import send_tally_request
from core.xml_sanitizer import sanitize_xml
from core.xml_parser import parse_xml, local_name, get_field


REQUEST_XML = """<?xml version="1.0" encoding="UTF-8"?>
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


def main():
    print("\nJTECH TALLY BRIDGE - COMPANY DISCOVERY")
    print("=" * 50)

    response = send_tally_request(REQUEST_XML)
    clean_xml, removed = sanitize_xml(response.content)
    root = parse_xml(clean_xml)

    companies = [
        element
        for element in root.iter()
        if local_name(element.tag) == "COMPANY"
    ]

    print("HTTP status:", response.status_code)
    print("Invalid XML references removed:", removed)
    print("Company records found:", len(companies))

    if not companies:
        print("\nNo COMPANY records found.")
        print("Check whether the response contains a Tally error.")
        return

    print("\nCompany metadata:")
    print("-" * 50)

    for index, company in enumerate(companies, start=1):
        name = company.attrib.get("NAME") or get_field(company, "NAME")
        starting_from = get_field(company, "STARTINGFROM")
        books_from = get_field(company, "BOOKSFROM")

        print(f"\nCompany #{index}")
        print("Name:", name or "Not returned")
        print("Starting from:", starting_from or "Not returned")
        print("Books from:", books_from or "Not returned")


if __name__ == "__main__":
    main()
