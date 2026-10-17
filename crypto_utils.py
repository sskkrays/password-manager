"""
Модуль криптографии.
Использует PBKDF2 для получения ключа из мастер-пароля
и Fernet (AES-128 в CBC + HMAC) для шифрования данных.
"""
import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Константы
SALT_SIZE = 16
ITERATIONS = 200_000
KDF_ALGO = hashes.SHA256()


def generate_salt() -> bytes:
    """Генерирует случайную соль."""
    return os.urandom(SALT_SIZE)


def derive_key(master_password: str, salt: bytes) -> bytes:
    """Выводит 32-байтный ключ из мастер-пароля и соли."""
    kdf = PBKDF2HMAC(
        algorithm=KDF_ALGO,
        length=32,
        salt=salt,
        iterations=ITERATIONS,
    )
    key = kdf.derive(master_password.encode("utf-8"))
    return base64.urlsafe_b64encode(key)


def hash_master_password(master_password: str, salt: bytes) -> str:
    """Хэш мастер-пароля для проверки при входе (не для восстановления)."""
    dk = hashlib.pbkdf2_hmac(
        "sha256", master_password.encode("utf-8"), salt, ITERATIONS
    )
    return base64.b64encode(dk).decode("utf-8")


class CryptoManager:
    """Обёртка над Fernet с хранением ключа в памяти."""

    def __init__(self, key: bytes):
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode("utf-8"))

    def decrypt(self, token: bytes) -> str:
        return self._fernet.decrypt(token).decode("utf-8")