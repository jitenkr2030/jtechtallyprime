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
<ID>JTech Voucher Type Verification</ID>
</HEADER>
<BODY>
<DESC>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
</STATICVARIABLES>
<TDL>
<TDLMESSAGE>
<COLLECTION NAME="JTech Voucher Type Verification">
<TYPE>VoucherType</TYPE>
<FETCH>Name, Parent, IsDeemedPositive, NumberingMethod,
IsReserved, UseForPOS, IsActive</FETCH>
</COLLECTION>
</TDLMESSAGE>
</TDL>
</DESC>
</BODY>
</ENVELOPE>"""


FIELDS = [
    "PARENT",
    "ISDEEMEDPOSITIVE",
    "NUMBERINGMETHOD",
    "ISRESERVED",
    "ISACTIVE",
    "USEFORPOS",
]


def main():
    response, company = send_company_request(REQUEST_XML)
    root, removed = parse_tally_response(response)

    distributions = {
        field: Counter()
        for field in FIELDS
    }

    named_records = 0

    for element in root.iter():
        if local_name(element.tag) != "VOUCHERTYPE":
            continue

        if not element.attrib.get("NAME"):
            continue

        named_records += 1

        for child in element:
            field = local_name(child.tag)

            if field in distributions:
                value = (child.text or "").strip().casefold()
                distributions[field][value or "<EMPTY>"] += 1

    print("\nVOUCHER TYPE FIELD VERIFICATION")
    print("=" * 48)
    print("Company ID:", company["id"])
    print("HTTP status:", response.status_code)
    print("Named Voucher Types:", named_records)
    print("Invalid XML references sanitized:", removed)

    for field, values in distributions.items():
        print(f"\n{field}:")
        if not values:
            print("  <FIELD NOT RETURNED>")
        else:
            for value, count in sorted(values.items()):
                print(f"  {value}: {count}")

    print("\nNo voucher type names or accounting values displayed.")


if __name__ == "__main__":
    main()
