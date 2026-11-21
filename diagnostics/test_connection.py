from core.connection_manager import (
    get_active_connection,
    test_connection
)


def main():
    print("\nJTECH TALLY BRIDGE")
    print("=" * 45)

    profile = get_active_connection()

    print("Profile:", profile["profile"])
    print("Host:", profile["host"])
    print("Port:", profile["port"])

    print("\nTesting TallyPrime connection...")

    result = test_connection()

    print("\nConnection successful!")
    print("Response:", result["message"])


if __name__ == "__main__":
    main()
