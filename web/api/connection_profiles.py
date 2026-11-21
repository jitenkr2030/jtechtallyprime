"""
JTech Tally Bridge - Multi-Tally connection manager

Allows multiple Tally instances to be registered and used as
sources. Profiles are stored in `app_settings` table under
keys `tally_profile_<n>` as JSON.

Each profile:
    {
        "name": str,
        "host": str,
        "port": int,
        "active": bool,
    }

The "active" profile overrides the host/port derived from .env
for the duration of a request.
"""

import json
from storage.database import get_connection
from config.logging_config import get_logger

log = get_logger(__name__)


def list_profiles():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT key, value FROM app_settings WHERE key LIKE 'tally_profile_%'"
        ).fetchall()
    profiles = []
    for row in rows:
        try:
            data = json.loads(row["value"])
            data["key"] = row["key"]
            profiles.append(data)
        except json.JSONDecodeError:
            log.warning("Corrupt profile %s ignored", row["key"])
    return profiles


def get_profile(name):
    for p in list_profiles():
        if p.get("name") == name:
            return p
    return None


def save_profile(name, host, port, active=False):
    key = f"tally_profile_{name.lower().replace(' ', '_')}"
    data = json.dumps({
        "name": name,
        "host": host,
        "port": int(port),
        "active": bool(active),
    })
    with get_connection() as conn:
        if active:
            conn.execute(
                """
                UPDATE app_settings
                SET value = json_set(value, '$.active', json('false'))
                WHERE key LIKE 'tally_profile_%'
                """
            )
        conn.execute(
            """
            INSERT INTO app_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, data),
        )
    return {"name": name, "host": host, "port": int(port), "active": bool(active)}


def delete_profile(name):
    key = f"tally_profile_{name.lower().replace(' ', '_')}"
    with get_connection() as conn:
        conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))


def get_active_profile():
    for p in list_profiles():
        if p.get("active"):
            return p
    return None
