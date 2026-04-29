from typing import Dict, List, Optional

from db.database import get_connection


def save_tokens(access_token: str, refresh_token: Optional[str], expiry: Optional[str]) -> None:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO tokens(id, access_token, refresh_token, expiry)
        VALUES(1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            access_token = excluded.access_token,
            refresh_token = COALESCE(excluded.refresh_token, tokens.refresh_token),
            expiry = excluded.expiry
        """,
        (access_token, refresh_token, expiry),
    )
    connection.commit()
    connection.close()


def get_tokens() -> Optional[Dict[str, str]]:
    connection = get_connection()
    cursor = connection.cursor()
    row = cursor.execute("SELECT access_token, refresh_token, expiry FROM tokens WHERE id = 1").fetchone()
    connection.close()
    if not row:
        return None
    return {
        "access_token": row["access_token"],
        "refresh_token": row["refresh_token"],
        "expiry": row["expiry"],
    }


def upsert_emails(emails: List[Dict[str, str]]) -> None:
    if not emails:
        return

    connection = get_connection()
    cursor = connection.cursor()
    cursor.executemany(
        """
        INSERT INTO emails(id, thread_id, subject, sender, body, snippet, date)
        VALUES(:id, :thread_id, :subject, :sender, :body, :snippet, :date)
        ON CONFLICT(id) DO UPDATE SET
            thread_id = excluded.thread_id,
            subject = excluded.subject,
            sender = excluded.sender,
            body = excluded.body,
            snippet = excluded.snippet,
            date = excluded.date
        """,
        emails,
    )
    connection.commit()
    connection.close()


def get_all_emails() -> List[Dict[str, str]]:
    connection = get_connection()
    cursor = connection.cursor()
    rows = cursor.execute(
        """
        SELECT id, thread_id, subject, sender, body, snippet, date
        FROM emails
        ORDER BY date DESC
        """
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def get_email_count() -> int:
    connection = get_connection()
    cursor = connection.cursor()
    row = cursor.execute("SELECT COUNT(*) AS total FROM emails").fetchone()
    connection.close()
    return int(row["total"])
