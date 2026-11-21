from collections import Counter

from core.tally_request import (
    send_company_request,
    parse_tally_response,
)
from core.xml_parser import local_name


REQUEST_XML = """<ENVELOPE>
<HEADER>
<VERSION>1</VERSION>
<TALLYREQUEST>EXPORT</TALLYREQUEST>
<TYPE>COLLECTION</TYPE>
<ID>JTech Voucher Type Fields</ID>
</HEADER>
<BODY>
<DESC>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
</STATICVARIABLES>
<TDL>
<TDLMESSAGE>
<COLLECTION NAME="JTech Voucher Type Fields">
<TYPE>VoucherType</TYPE>
<FETCH>Name, Parent, IsDeemedPositive, NumberingMethod,
IsReserved, UseForPOS, IsActive</FETCH>
</COLLECTION>
</TDLMESSAGE>
</TDL>
</DESC>
</BODY>
</ENVELOPE>"""


def main():
    response, company = send_company_request(REQUEST_XML)
    root, removed = parse_tally_response(response)

    element_counts = Counter()
    attribute_counts = Counter()
    voucher_type_count = 0

    for element in root.iter():
        tag = local_name(element.tag)
        element_counts[tag] += 1

        if tag == "VOUCHERTYPE":
            voucher_type_count += 1

            for attribute in element.attrib:
                attribute_counts[local_name(attribute)] += 1

    print("\nVOUCHER TYPE XML STRUCTURE PROBE")
    print("=" * 48)
    print("Company ID:", company["id"])
    print("HTTP status:", response.status_code)
    print("Voucher Type elements:", voucher_type_count)
    print("Invalid XML references sanitized:", removed)

    print("\nXML element frequency:")
    for field, count in sorted(element_counts.items()):
        print(f"  {field}: {count}")

    print("\nVoucher Type attribute frequency:")
    for field, count in sorted(attribute_counts.items()):
        print(f"  {field}: {count}")

    print("\nNo voucher type names or accounting values displayed.")


if __name__ == "__main__":
    main()
