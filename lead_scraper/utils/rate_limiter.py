"""Small rate-limit and request logging helpers."""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class RequestLogger:
    dry_run: bool = False
    entries: list[str] = field(default_factory=list)

    def log(self, source: str, action: str, target: str) -> None:
        prefix = "DRY-RUN" if self.dry_run else "REQUEST"
        message = f"{prefix} [{source}] {action}: {target}"
        self.entries.append(message)
        log.info(message)


class RateLimiter:
    def __init__(self, max_per_minute: int):
        self.interval = 60.0 / max(1, max_per_minute)
        self.last_request = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self.last_request
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self.last_request = time.monotonic()


def randomized_delay(min_seconds: float, max_seconds: float) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))
