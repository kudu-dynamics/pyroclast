import os

import pytest

import pyroclast.data.redis as KV
from tests import should_skip


pytestmark = pytest.mark.skipif(should_skip("redis"), reason=f"flag set to skip {__name__}")

HOST = os.getenv("REDIS_HOST", "127.0.0.1")
PORT = os.getenv("REDIS_PORT", "6379")


def test_basic_kv():
    client = KV.connect(host=HOST, port=PORT)
    client.kv_pop("hello")
    assert not client.kv_get("hello")
    client.kv_set("hello", "world")
    assert client.kv_get("hello") == b"world"
