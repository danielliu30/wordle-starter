import asyncio
import contextvars

import pytest

from app.timeout import execute_with_timeout

trace_id = contextvars.ContextVar("trace_id", default="old")


def test_outer_deadline_expiry_reports_configured_timeout():
    with pytest.raises(TimeoutError, match="after 0.01 seconds"):
        asyncio.run(execute_with_timeout(asyncio.sleep(1), 0.01))


def test_inner_timeout_error_is_preserved():
    async def operation():
        raise TimeoutError("redis socket timeout")

    with pytest.raises(TimeoutError, match="^redis socket timeout$"):
        asyncio.run(execute_with_timeout(operation(), 30))


def test_context_changes_remain_visible_to_caller():
    async def operation():
        trace_id.set("new")
        return "done"

    async def caller():
        result = await execute_with_timeout(operation(), 30)
        return result, trace_id.get()

    assert asyncio.run(caller()) == ("done", "new")
