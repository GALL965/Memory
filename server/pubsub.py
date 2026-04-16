from __future__ import annotations

import queue
import threading
import uuid


class SubscriberHub:
    """Simple pub/sub hub for server-side streaming updates."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: dict[str, queue.Queue] = {}

    def add(self) -> tuple[str, queue.Queue]:
        sub_id = str(uuid.uuid4())
        q: queue.Queue = queue.Queue(maxsize=100)
        with self._lock:
            self._subscribers[sub_id] = q
        return sub_id, q

    def remove(self, sub_id: str) -> None:
        with self._lock:
            self._subscribers.pop(sub_id, None)

    def publish(self, item: object) -> None:
        with self._lock:
            subscribers = list(self._subscribers.values())

        for q in subscribers:
            try:
                q.put_nowait(item)
            except queue.Full:
                # Best-effort: drop update if a client is too slow.
                pass
