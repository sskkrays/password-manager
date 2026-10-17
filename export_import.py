"""
Экспорт/импорт базы.
Формат JSON (внутри — base64 от шифртекста).
Данные остаются зашифрованными — импорт требует тот же мастер-пароль.
"""
import json
import base64
from typing import List, Dict
from database import Database
from crypto_utils import CryptoManager


def _to_b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _from_b64(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


def export_to_json(db: Database, filepath: str) -> int:
    """Экспортирует записи (в зашифрованном виде) в JSON. Возвращает число записей."""
    entries = db.get_all_entries()
    data = {
        "version": 1,
        "entries": [
            {
                "title": _to_b64(e["title"]),
                "username": _to_b64(e["username"]),
                "password": _to_b64(e["password"]),
                "notes": _to_b64(e["notes"] or b""),
            }
            for e in entries
        ],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return len(entries)


def import_from_json(db: Database, crypto: CryptoManager, filepath: str) -> int:
    """
    Импортирует записи. Проверяет, что мастер-пароль подходит
    (пытаясь расшифровать первую запись). Возвращает число импортированных.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("entries", [])
    imported = 0
    for i, e in enumerate(entries):
        title = _from_b64(e["title"])
        username = _from_b64(e["username"])
        password = _from_b64(e["password"])
        notes = _from_b64(e["notes"]) if e.get("notes") else b""

        # На первой записи проверяем ключ
        if i == 0:
            try:
                crypto.decrypt(password)
            except Exception as exc:
                raise ValueError(
                    "Не удалось расшифровать импортируемые данные: "
                    "неверный мастер-пароль или файл повреждён."
                ) from exc

        db.add_entry(title, username, password, notes)
        imported += 1
    return imported