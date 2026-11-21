from storage.company_registry import (
    sync_companies,
    get_selected_company,
)


def main():
    print("\nJTECH TALLY BRIDGE - COMPANY REGISTRY")
    print("=" * 50)

    companies = sync_companies()

    print("Companies synchronized:", len(companies))
    print("\nDiscovered companies:")
    print("-" * 50)

    for company in companies:
        print(
            f"ID: {company['id']} | "
            f"Name: {company['name']}"
        )

    selected = get_selected_company()

    print("\nSelected company:")

    if selected:
        print(f"ID: {selected['id']} | Name: {selected['name']}")
    else:
        print("No company selected. This is expected initially.")

    print("\nRegistry synchronization completed.")


if __name__ == "__main__":
    main()
