"""
JTech Tally Bridge - Group Reader Test

Runs Group Master export and performs basic quality checks.
Does not print actual group names or accounting values.
"""

from collections import Counter

from modules.group_reader import read_groups


def main():
    groups = read_groups()

    names = [
        group.get("name", "").strip().casefold()
        for group in groups
    ]

    duplicates = [
        name
        for name, count in Counter(names).items()
        if name and count > 1
    ]

    empty_names = sum(not name for name in names)

    parent_count = sum(
        bool(group.get("parent"))
        for group in groups
    )

    primary_group_count = sum(
        bool(group.get("primary_group"))
        for group in groups
    )

    print("\nGROUP MASTER QUALITY CHECK")
    print("=" * 45)
    print("Total records:", len(groups))
    print("Unique group names:", len(set(names)))
    print("Duplicate names:", len(duplicates))
    print("Empty names:", empty_names)
    print("Groups with parent populated:", parent_count)
    print("Groups with primary group populated:", primary_group_count)

    print("\nNo group names or accounting values displayed.")


if __name__ == "__main__":
    main()
