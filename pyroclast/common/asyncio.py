"""
Provide a mechanism to call into asyncio code from synchronous code.

## Thread Safety

This notably spawns a new thread to run an asyncio loop and most likely provides
similar constraints to the github.com/dpkp/kafka-python package.

Producers are likely safe to be used across threads, but not consumers.
"""
import asyncio
import threading
from typing import Any


# DEV: Should we create a separate loop per asyncio subsystem?
__all__ = ["sync_await"]
_loop = None


def sync_await(coroutine) -> Any:
    return asyncio.run_coroutine_threadsafe(coroutine, _event_loop()).result()


def _event_loop() -> asyncio.BaseEventLoop:
    global _loop
    if _loop is None:
        _loop = asyncio.new_event_loop()
        thread = threading.Thread(target=_loop.run_forever)
        thread.setDaemon(True)
        thread.start()
    return _loop
