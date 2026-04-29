import os
import sqlite3


def get_db_path() -> str:
    return os.getenv("DATABASE_PATH", "./email_rag.db")


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(get_db_path(), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS emails(
            id TEXT PRIMARY KEY,
            thread_id TEXT,
            subject TEXT,
            sender TEXT,
            body TEXT,
            snippet TEXT,
            date TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tokens(
            id INTEGER PRIMARY KEY CHECK(id = 1),
            access_token TEXT NOT NULL,
            refresh_token TEXT,
            expiry TEXT
        )
        """
    )

    columns = {row[1] for row in cursor.execute("PRAGMA table_info(emails)").fetchall()}
    if "thread_id" not in columns:
        cursor.execute("ALTER TABLE emails ADD COLUMN thread_id TEXT")

    connection.commit()
    connection.close()
