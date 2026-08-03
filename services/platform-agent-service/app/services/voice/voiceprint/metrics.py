"""声纹结构化日志。"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("app.voiceprint")


def log_voiceprint_event(event: str, **fields: Any) -> None:
    parts = [f"event={event}"]
    for key, value in fields.items():
        if value is None:
            continue
        parts.append(f"{key}={value}")
    logger.info(" ".join(parts))
