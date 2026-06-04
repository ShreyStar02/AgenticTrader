"""Password hashing/verification for paper-fund authorization (local only).

Uses bcrypt directly (passlib is incompatible with bcrypt>=5). bcrypt limits
inputs to 72 bytes, so we pre-hash with SHA-256 to support arbitrary-length passwords.
"""
from __future__ import annotations

import base64
import hashlib

import bcrypt


def _prep(plain: str) -> bytes:
    digest = hashlib.sha256(plain.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_prep(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prep(plain), hashed.encode("utf-8"))
    except Exception:
        return False
