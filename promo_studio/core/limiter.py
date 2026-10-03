from __future__ import annotations

import threading
import time


class RateLimiter:
    """Blocks so that no more than `calls_per_minute` calls start in any 60 seconds."""

    def __init__(self, calls_per_minute: int, clock=time.monotonic, sleep=time.sleep):
        self.capacity = max(int(calls_per_minute), 1)
        self._clock, self._sleep = clock, sleep
        self._stamps: list[float] = []
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = self._clock()
                self._stamps = [t for t in self._stamps if now - t < 60]
                if len(self._stamps) < self.capacity:
                    self._stamps.append(now)
                    return
                wait = 60 - (now - self._stamps[0])
            self._sleep(max(wait, 0.05))
