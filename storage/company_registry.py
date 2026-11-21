"""
JTech Tally Bridge - Company Registry

Synchronizes discovered Tally companies with SQLite.
Company selection is always explicit.
"""

from storage.database import get_connection, initialize_database
from modules.company_reader import read_companies


def sync_companies():
    initialize_database()

    result = read_companies()

    with get_connection() as connection:
        for company in result["companies"]:
            connection.execute("""
                INSERT INTO companies (
                    name,
                    reserved_name,
                    starting_from,
                    books_from
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    reserved_name = excluded.reserved_name,
                    starting_from = excluded.starting_from,
                    books_from = excluded.books_from,
                    last_seen_at = CURRENT_TIMESTAMP
            """, (
                company["name"],
                company["reserved_name"],
                company["starting_from"],
                company["books_from"],
            ))

    return list_companies()


def list_companies():
    initialize_database()

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, name, reserved_name,
                   starting_from, books_from, last_seen_at
            FROM companies
            ORDER BY id
        """).fetchall()

    return [dict(row) for row in rows]


def select_company(company_id):
    initialize_database()

    with get_connection() as connection:
        company = connection.execute(
            "SELECT id, name FROM companies WHERE id = ?",
            (company_id,)
        ).fetchone()

        if company is None:
            raise ValueError(f"Company ID {company_id} does not exist.")

        connection.execute("""
            INSERT INTO app_settings (key, value)
            VALUES ('selected_company_id', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (str(company_id),))

    return dict(company)


def get_selected_company():
    initialize_database()

    with get_connection() as connection:
        setting = connection.execute("""
            SELECT value FROM app_settings
            WHERE key = 'selected_company_id'
        """).fetchone()

        if setting is None:
            return None

        company = connection.execute(
            "SELECT * FROM companies WHERE id = ?",
            (setting["value"],)
        ).fetchone()

    return dict(company) if company else None
