"""

"""
from typing import Any, Optional

import redis

import pyroclast.common.kv as KV


# kv interface


def connect(*args, **kwargs) -> KV.Client:
    """Connect to Redis server.

    Parameters
    ----------
    host : str
        The host string of a server (e.g. redis.service.consul)
    port : Union[int, str], optional
        The Redis port. Defaults to 6379.
    db : Union[int, str], optional
        The redis db. Defaults to 0.
    """
    host = kwargs["host"]
    port = kwargs.get("port", 6379)
    db = kwargs.get("db", 0)

    # Make convenience bindings for the client.
    conn = redis.Redis(host=host, port=port, db=db)
    client = KV.Client(conn, name="redis")
    for sym in KV.Symbols:
        setattr(client, sym, globals()[sym].__get__(client))
    return client


def kv_get(client: KV.Client, name: str, **kwargs) -> Optional[bytes]:
    return client.raw_client.get(name)


def kv_set(client: KV.Client, name, value: str, **kwargs) -> Optional[Any]:
    """
    Mirror the functionality of the raw clients' set method and return the
    client itself.
    """
    client.raw_client.set(name, value, **kwargs)
    return client


def kv_pop(client: KV.Client, name: str, *args, **kwargs) -> Optional[Any]:
    return client.raw_client.delete(name)
