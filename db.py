import sqlite3
from pathlib import Path


DB_PATH = Path("emails.db")


class EmailRepository:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = str(db_path)
        self._initialize_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _initialize_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_emails (
                    email_id TEXT PRIMARY KEY
                )
            """)
            conn.commit()

    def is_processed(self, email_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT 1
                FROM processed_emails
                WHERE email_id = ?
                LIMIT 1
                """,
                (email_id,)
            )

            return cursor.fetchone() is not None

    def mark_processed(self, email_id: str):
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO processed_emails (email_id)
                VALUES (?)
                """,
                (email_id,)
            )
            conn.commit()