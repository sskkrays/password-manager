"""
Модуль работы с SQLite.
Хранит: соль, хэш мастер-пароля, зашифрованные записи.
"""
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict

DB_PATH = Path("vault.db")


class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        # Таблица мета-информации (соль, проверочный хэш)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                salt BLOB NOT NULL,
                master_hash TEXT NOT NULL,
                check_token BLOB NOT NULL
            )
        """)
        # Таблица записей
        cur.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title BLOB NOT NULL,
                username BLOB NOT NULL,
                password BLOB NOT NULL,
                notes BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    # ---- Мета ----
    def is_initialized(self) -> bool:
        cur = self.conn.execute("SELECT 1 FROM meta WHERE id = 1")
        return cur.fetchone() is not None

    def save_meta(self, salt: bytes, master_hash: str, check_token: bytes) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO meta (id, salt, master_hash, check_token) VALUES (1, ?, ?, ?)",
            (salt, master_hash, check_token),
        )
        self.conn.commit()

    def get_meta(self) -> Optional[Dict]:
        row = self.conn.execute("SELECT * FROM meta WHERE id = 1").fetchone()
        return dict(row) if row else None

    # ---- Записи ----
    def add_entry(self, title: bytes, username: bytes,
                  password: bytes, notes: bytes) -> int:
        cur = self.conn.execute(
            "INSERT INTO entries (title, username, password, notes) VALUES (?, ?, ?, ?)",
            (title, username, password, notes),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_entry(self, entry_id: int, title: bytes, username: bytes,
                     password: bytes, notes: bytes) -> None:
        self.conn.execute(
            """UPDATE entries
               SET title=?, username=?, password=?, notes=?,
                   updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (title, username, password, notes, entry_id),
        )
        self.conn.commit()

    def delete_entry(self, entry_id: int) -> None:
        self.conn.execute("DELETE FROM entries WHERE id=?", (entry_id,))
        self.conn.commit()

    def get_all_entries(self) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM entries ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_entry(self, entry_id: int) -> Optional[Dict]:
        row = self.conn.execute(
            "SELECT * FROM entries WHERE id=?", (entry_id,)
        ).fetchone()
        return dict(row) if row else None

    def close(self) -> None:
        self.conn.close()