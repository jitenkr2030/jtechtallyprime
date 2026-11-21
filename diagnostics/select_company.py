from storage.company_registry import (
    list_companies,
    select_company,
    get_selected_company,
)


def main():
    print("\nJTECH TALLY BRIDGE - COMPANY SELECTION")
    print("=" * 50)

    companies = list_companies()

    if not companies:
        print("No companies registered.")
        print("Run company synchronization first.")
        return

    print("\nAvailable companies:")

    for company in companies:
        print(f"\nID: {company['id']}")
        print(f"Name: {company['name']}")

    current = get_selected_company()

    if current:
        print(f"\nCurrently selected ID: {current['id']}")
    else:
        print("\nNo company currently selected.")

    choice = input("\nEnter company ID to select: ").strip()

    if not choice.isdigit():
        print("Invalid company ID.")
        return

    try:
        selected = select_company(int(choice))
    except ValueError as exc:
        print("Selection failed:", exc)
        return

    print("\nCompany selected successfully.")
    print("Selected company ID:", selected["id"])
    print("Company selection saved in SQLite.")


if __name__ == "__main__":
    main()
