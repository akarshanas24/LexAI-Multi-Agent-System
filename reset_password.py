import argparse
import sqlite3
from pathlib import Path

from auth.auth import hash_password
from config.settings import settings


def _sqlite_path() -> Path:
    prefix = "sqlite+aiosqlite:///"
    url = settings.DATABASE_URL
    if not url.startswith(prefix):
        raise SystemExit(f"Unsupported DATABASE_URL for this utility: {url}")
    raw_path = url[len(prefix):]
    return Path(raw_path).resolve()


def list_users(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "select username, email, is_active from users order by lower(username)"
    ).fetchall()
    if not rows:
        print("No users found.")
        return
    for username, email, is_active in rows:
        status = "active" if is_active else "disabled"
        print(f"{username} | {email} | {status}")


def reset_password(conn: sqlite3.Connection, identifier: str, password: str) -> None:
    normalized = identifier.strip().lower()
    row = conn.execute(
        """
        select id, username, email
        from users
        where lower(username) = ? or lower(email) = ?
        limit 1
        """,
        (normalized, normalized),
    ).fetchone()
    if not row:
        raise SystemExit(f"No user found for '{identifier}'.")

    user_id, username, email = row
    hashed = hash_password(password)
    conn.execute(
        "update users set hashed_password = ? where id = ?",
        (hashed, user_id),
    )
    conn.commit()
    print(f"Password reset for {username} ({email}).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset a local LexAI user's password.")
    parser.add_argument("--list", action="store_true", help="List local users.")
    parser.add_argument("--identifier", help="Username or email for the user to reset.")
    parser.add_argument("--password", help="New password to set.")
    args = parser.parse_args()

    db_path = _sqlite_path()
    if not db_path.exists():
        raise SystemExit(f"Database file not found: {db_path}")

    with sqlite3.connect(db_path) as conn:
        if args.list:
            list_users(conn)
            return
        if not args.identifier or not args.password:
            raise SystemExit("Use --list or provide both --identifier and --password.")
        reset_password(conn, args.identifier, args.password)


if __name__ == "__main__":
    main()
