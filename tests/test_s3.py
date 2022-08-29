import pytest

import pyroclast.data.s3 as KV
from tests import should_skip


pytestmark = pytest.mark.skipif(should_skip("s3"), reason=f"flag set to skip {__name__}")


def test_basic_kv():
    client = KV.connect()

    # First, create a test bucket.
    client.kv_set("test")

    client.kv_pop("test", "hello")
    assert not client.kv_get("test", "hello")
    client.kv_set("test", "hello", "world".encode())
    assert client.kv_get("test", "hello").read() == b"world"
