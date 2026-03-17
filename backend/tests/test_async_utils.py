from __future__ import annotations

import asyncio

from backend.core.async_utils import run_async_blocking


async def _value_after_yield(value: int) -> int:
    await asyncio.sleep(0)
    return value


def test_run_async_blocking_without_running_loop() -> None:
    result = run_async_blocking(lambda: _value_after_yield(7))
    assert result == 7


def test_run_async_blocking_with_running_loop() -> None:
    async def _main() -> int:
        return run_async_blocking(lambda: _value_after_yield(11))

    result = asyncio.run(_main())
    assert result == 11
