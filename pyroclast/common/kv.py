"""
Pyroclast has connectors for various systems that can be treated as
key value stores.

# Backends

The currently supported kv backends include:

- Redis
- S3
"""
from typing import Any, Optional

from pyroclast.common import AbstractClient


Client = AbstractClient
Symbols = ["kv_get", "kv_set", "kv_pop"]


# Any kv wrapper must provide the following methods.


def connect(*args, **kwargs) -> Client:  # pragma: nocover
    raise NotImplementedError


def disconnect(client: Client, *args, **kwargs) -> Optional[Any]:  # pragma: nocover
    raise NotImplementedError


def kv_get(client: Client, *args, **kwargs) -> Optional[Any]:  # pragma: nocover
    raise NotImplementedError


def kv_set(client: Client, *args, **kwargs) -> Optional[Any]:  # pragma: nocover
    raise NotImplementedError


def kv_pop(client: Client, *args, **kwargs) -> Optional[Any]:  # pragma: nocover
    raise NotImplementedError
