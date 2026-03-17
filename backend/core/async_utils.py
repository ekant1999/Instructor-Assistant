from __future__ import annotations

import asyncio
import queue
import threading
from typing import Awaitable, Callable, TypeVar


T = TypeVar("T")


def run_async_blocking(coro_factory: Callable[[], Awaitable[T]]) -> T:
    """
    Run an async callable from sync code.

    If there is no running event loop in the current thread, this uses
    ``asyncio.run`` directly. If a loop is already running, it executes the
    coroutine in a short-lived background thread with its own event loop.
    """

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())

    result_queue: queue.Queue[tuple[bool, object]] = queue.Queue(maxsize=1)

    def _runner() -> None:
        try:
            result = asyncio.run(coro_factory())
        except BaseException as exc:  # pragma: no cover - exercised via caller
            result_queue.put((False, exc))
        else:
            result_queue.put((True, result))

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    ok, payload = result_queue.get()
    if ok:
        return payload  # type: ignore[return-value]
    raise payload  # type: ignore[misc]
