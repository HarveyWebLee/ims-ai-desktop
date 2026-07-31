"""JWT payload 工具（不依赖 FastAPI），供写操作补全 username。"""

from __future__ import annotations

import base64
import json


def decode_jwt_payload(token: str) -> dict:
    raw = (token or "").replace("Bearer ", "").strip()
    parts = raw.split(".")
    if len(parts) != 3:
        return {}
    segment = parts[1]
    pad = (-len(segment)) % 4
    if pad:
        segment += "=" * pad
    try:
        decoded = base64.urlsafe_b64decode(segment.encode("ascii"))
        data = json.loads(decoded.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except ValueError, json.JSONDecodeError, UnicodeDecodeError:
        return {}


def get_username_from_token(authorization: str | None) -> str | None:
    token = (authorization or "").replace("Bearer ", "").strip()
    if not token:
        return None
    payload = decode_jwt_payload(token)
    for key in ("username", "userName", "sub", "name"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
