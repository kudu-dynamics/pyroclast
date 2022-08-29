"""
Provide a synchronous [Sonic client](https://github.com/valeriansaliou/sonic).
"""
from typing import List

import asonic
from asonic.enums import Channels

from pyroclast.common.asyncio import sync_await
import pyroclast.common.kv as KV


# kv interface


def connect(*args, **kwargs) -> KV.Client:
    """Connect to Sonic.

    Parameters
    ----------
    """
    conn_args = {"host": kwargs["host"], "port": kwargs.get("port", 1491)}
    raw_client = asonic.Client(**conn_args)

    client = KV.Client(raw_client, name="sonic", **conn_args)
    for sym in KV.Symbols:
        setattr(client, sym, globals()[sym].__get__(client))
    return client


def disconnect(client: KV.Client, *args, **kwargs):
    sync_await(client.raw_client.quit())


def _swap_channel(client: KV.Client, target_channel: str):
    if target_channel not in [member.value for member in Channels]:
        raise ValueError(f"Sonic has no such Channel: {target_channel}")
    if client.raw_client._channel not in (Channels.UNINITIALIZED.value, target_channel):
        # DEV: Sonic does not allow for channel switching.
        #      A client reconnect must be first forced.
        disconnect(client)
        client.raw_client = connect(**client.meta).raw_client
    if client.raw_client._channel != target_channel:
        # Connect to the desired channel.
        sync_await(client.raw_client.channel(target_channel))


def kv_get(client: KV.Client, collection, bucket: str, *args, **kwargs) -> List[bytes]:
    _swap_channel(client, Channels.SEARCH.value)
    return sync_await(client.raw_client.query(collection, bucket, *args))


def kv_set(client: KV.Client, collection, bucket, obj, text: str, **kwargs) -> bytes:
    _swap_channel(client, Channels.INGEST.value)
    return sync_await(client.raw_client.push(collection, bucket, obj, text, **kwargs))


def kv_pop(client: KV.Client, collection, bucket, obj, text: str, **kwargs) -> int:
    _swap_channel(client, Channels.INGEST.value)
    return sync_await(client.raw_client.pop(collection, bucket, obj, text, **kwargs))
