import os

import pytest

import pyroclast.data.sonic as KV
from tests import should_skip


pytestmark = pytest.mark.skipif(should_skip("sonic"), reason=f"flag set to skip {__name__}")

HOST = os.getenv("SONIC_HOST", "127.0.0.1")
PORT = os.getenv("SONIC_PORT", "1491")


def test_basic_kv():
    client = KV.connect(host=HOST, port=PORT)

    collection = "test"
    bucket = "bucket"
    obj = "obj-1"
    text = "example"

    client.kv_pop(collection, bucket, obj, text)
    assert not client.kv_get(collection, bucket, text)
    client.kv_set(collection, bucket, obj, text)
    results = client.kv_get(collection, bucket, text)
    assert len(results) == 1
    assert results[0] == obj.encode()
