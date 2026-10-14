




from __future__ import annotations

import base64
import hashlib
import os
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

DEFAULT_DB = Path.home() / ".config/vladmir/mobile-devices.db"
CLOCK_SKEW = 60
_SAFE_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_B64_DATA = re.compile(r"[A-Za-z0-9_-]+\Z")


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def unb64(value: str) -> bytes:
    if not isinstance(value, str) or not value or len(value) > 4096 or not _B64_DATA.fullmatch(value):
        raise ValueError("codificação inválida")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def signed_message(method: str, path: str, body: bytes, timestamp: str, nonce: str) -> bytes:
    return "\n".join(("Vladmir-MOBILE-V1", method, path, hashlib.sha256(body).hexdigest(), timestamp, nonce)).encode("ascii")


def session_message(method: str, path: str, body: bytes, timestamp: str, nonce: str,
                    request_id: str, token: str) -> bytes:

    return "\n".join(("Vladmir-MOBILE-V2", method, path, hashlib.sha256(body).hexdigest(),
                      timestamp, nonce, request_id, hashlib.sha256(token.encode("ascii")).hexdigest())).encode("ascii")


class SessionRegistry:

    def __init__(self, devices: "DeviceRegistry", lifetime: int = 300):
        self.devices = devices
        self.lifetime = lifetime
        self.lock = threading.RLock()
        self.sessions: dict[str, tuple[str, float, int]] = {}

    def issue(self, device_id: str) -> tuple[str, int]:
        token = secrets.token_urlsafe(32)
        now = time.time()


        with self.devices.lock, self.lock:
            active, generation = self.devices.session_state(device_id)
            if not active:
                raise ValueError("aparelho não autorizado")
            self.sessions = {digest: item for digest, item in self.sessions.items()
                             if item[1] > now and item[2] == generation}

            owned = [digest for digest, item in self.sessions.items() if item[0] == device_id]
            for digest in owned[:-7]:
                del self.sessions[digest]
            if len(self.sessions) >= 256:
                raise ValueError("limite de sessões atingido")
            self.sessions[hashlib.sha256(token.encode("ascii")).hexdigest()] = (
                device_id, now + self.lifetime, generation)
        return token, int(now + self.lifetime)

    def valid(self, device_id: str, token: str) -> bool:
        if not isinstance(token, str) or not token or len(token) > 128:
            return False
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self.devices.lock, self.lock:
            active, generation = self.devices.session_state(device_id)
            if not active:
                return False
            row = self.sessions.get(digest)
            return bool(row and row[0] == device_id and row[1] > time.time()
                        and row[2] == generation)

    def clear(self) -> None:
        with self.lock:
            self.sessions.clear()


class DeviceRegistry:
    def __init__(self, path: Path = DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path.parent.chmod(0o700)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False, timeout=5)
        self.path.chmod(0o600)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS enrollment (
              code_hash TEXT PRIMARY KEY, expires INTEGER NOT NULL, used INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS devices (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, public_key BLOB NOT NULL,
              status TEXT NOT NULL, added INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS nonces (
              device_id TEXT NOT NULL, nonce TEXT NOT NULL, expires INTEGER NOT NULL,
              PRIMARY KEY(device_id, nonce));
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        self.db.execute("INSERT OR IGNORE INTO settings VALUES('security_generation', '0')")
        self.db.commit()

    def close(self):
        self.db.close()

    def lockdown(self) -> bool:
        with self.lock:
            row = self.db.execute("SELECT value FROM settings WHERE key='lockdown'").fetchone()
            return bool(row and row[0] == "1")

    def set_lockdown(self, enabled: bool):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES('lockdown', ?)", ("1" if enabled else "0",))
            self._advance_generation()
            if enabled:
                self.db.execute("DELETE FROM enrollment")
                self.db.execute("UPDATE devices SET status='revoked' WHERE status='pending'")

    def _advance_generation(self) -> None:
        self.db.execute("UPDATE settings SET value=CAST(value AS INTEGER)+1 WHERE key='security_generation'")

    def session_state(self, device_id: str) -> tuple[bool, int]:

        with self.lock:
            row = self.db.execute("""
                SELECT d.status, (SELECT value FROM settings WHERE key='lockdown'),
                       (SELECT value FROM settings WHERE key='security_generation')
                FROM devices AS d WHERE d.id=?
            """, (device_id,)).fetchone()
            return (bool(row and row[0] == "authorized" and row[1] != "1"),
                    int(row[2]) if row else -1)

    def open_enrollment(self) -> str:
        with self.lock, self.db:
            if self.lockdown():
                raise ValueError("Vladmir está em lockdown")
            code = secrets.token_urlsafe(24)
            self.db.execute("DELETE FROM enrollment")
            self.db.execute("INSERT INTO enrollment VALUES(?, ?, 0)",
                            (hashlib.sha256(code.encode()).hexdigest(), int(time.time()) + 300))
            return code

    def enroll(self, code: str, name: str, public_der_b64: str, proof_b64: str) -> str:
        if not all(isinstance(value, str) for value in (code, name, public_der_b64, proof_b64)) or not 1 <= len(name) <= 60 or not 1 <= len(code) <= 100:
            raise ValueError("dados inválidos")
        public_der = unb64(public_der_b64)
        if len(public_der) > 512:
            raise ValueError("chave grande demais")
        key = serialization.load_der_public_key(public_der)
        if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(key.curve, ec.SECP256R1):
            raise ValueError("use chave EC P-256")
        try:
            key.verify(unb64(proof_b64), b"Vladmir-PAIR-V1\n" + code.encode(), ec.ECDSA(hashes.SHA256()))
        except InvalidSignature as exc:
            raise ValueError("prova de posse inválida") from exc
        digest = hashlib.sha256(code.encode()).hexdigest()
        with self.lock, self.db:
            if self.lockdown():
                raise ValueError("Vladmir está em lockdown")
            row = self.db.execute("SELECT expires, used FROM enrollment WHERE code_hash=?", (digest,)).fetchone()
            if not row or row[1] or row[0] < time.time():
                raise ValueError("pareamento expirado ou já usado")
            device_id = b64(hashlib.sha256(public_der).digest())
            self.db.execute("UPDATE enrollment SET used=1 WHERE code_hash=?", (digest,))
            self.db.execute("INSERT OR REPLACE INTO devices VALUES(?, ?, ?, 'pending', ?)",
                            (device_id, name, public_der, int(time.time())))
            self._advance_generation()
            return device_id

    def status(self, device_id: str) -> str:
        with self.lock:
            row = self.db.execute("SELECT status FROM devices WHERE id=?", (device_id,)).fetchone()
            return row[0] if row else "unknown"

    def list_devices(self) -> list[tuple[str, str, str]]:
        with self.lock:
            return self.db.execute("SELECT id, name, status FROM devices ORDER BY added DESC").fetchall()

    def update_device(self, device_id: str, status: str) -> bool:
        if status not in {"authorized", "revoked"}:
            raise ValueError("estado inválido")
        with self.lock, self.db:
            if status == "authorized" and self.lockdown():
                raise ValueError("Vladmir está em lockdown")
            if status == "authorized":
                changed = self.db.execute("UPDATE devices SET status='authorized' WHERE id=? AND status='pending'",
                                          (device_id,)).rowcount
            else:
                changed = self.db.execute("UPDATE devices SET status='revoked' WHERE id=? AND status IN ('pending','authorized')",
                                          (device_id,)).rowcount
            if changed:
                self._advance_generation()
            return bool(changed)

    def verify(self, device_id: str, method: str, path: str, body: bytes,
               timestamp: str, nonce: str, signature: str,
               request_id: str = "", session_token: str = "") -> bool:
        if (not isinstance(device_id, str) or len(device_id) != 43 or not _SAFE_ID.fullmatch(device_id)
                or not isinstance(nonce, str) or not _SAFE_ID.fullmatch(nonce)):
            return False
        try:
            if not isinstance(timestamp, str) or not re.fullmatch(r"[0-9]{1,12}", timestamp):
                return False
            seconds = int(timestamp)
            if abs(time.time() - seconds) > CLOCK_SKEW:
                return False
            if bool(request_id) != bool(session_token):
                return False
            if request_id and (not _SAFE_ID.fullmatch(request_id) or len(session_token) > 128
                               or not _SAFE_ID.fullmatch(session_token)):
                return False
            data = (session_message(method, path, body, timestamp, nonce, request_id, session_token)
                    if session_token else signed_message(method, path, body, timestamp, nonce))
            decoded = unb64(signature)
        except (ValueError, UnicodeError):
            return False
        with self.lock, self.db:
            if self.lockdown():
                return False
            row = self.db.execute("SELECT public_key FROM devices WHERE id=? AND status='authorized'",
                                  (device_id,)).fetchone()
            if not row:
                return False
            try:
                key = serialization.load_der_public_key(row[0])
                key.verify(decoded, data, ec.ECDSA(hashes.SHA256()))
            except (InvalidSignature, ValueError):
                return False
            self.db.execute("DELETE FROM nonces WHERE expires < ?", (int(time.time()),))
            try:
                self.db.execute("INSERT INTO nonces VALUES(?, ?, ?)",
                                (device_id, nonce, seconds + CLOCK_SKEW))
            except sqlite3.IntegrityError:
                return False
            return True
