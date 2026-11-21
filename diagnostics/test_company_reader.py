from modules.company_reader import read_companies


def main():
    print("\nJTECH TALLY BRIDGE - COMPANY READER")
    print("=" * 50)

    result = read_companies()

    print("HTTP status:", result["http_status"])
    print("Invalid XML references removed:",
          result["invalid_references_removed"])
    print("Actual companies:", result["total_companies"])

    for index, company in enumerate(result["companies"], start=1):
        print(f"\nCompany #{index}")
        print("Name:", company["name"])
        print("Starting from:", company["starting_from"])
        print("Books from:", company["books_from"])


if __name__ == "__main__":
    main()
