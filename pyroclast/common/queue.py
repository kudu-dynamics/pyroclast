"""
Pyroclast has connectors for various message broker systems.

Some of the use cases may involve:

- "I just want to receive messages off a stream"
- "I want to pick up where I left off in case I disconnect"
- "I am new and want to read the entire history of the stream"
- "I want exactly once processing"
- "I want to share the work of processing messages"

https://nats.io/blog/use-cases-for-persistent-logs-with-nats-streaming/

# Brokers

The currently supported brokers include:

- NATS
- NATS Streaming

The brokers we expect to support in the future include:

- Kafka
"""
from typing import Any, Iterator, Optional

from pyroclast.common import AbstractClient


Client = AbstractClient
Msg = Any


# Any queue wrapper must provide the following methods.


def connect(**kwargs) -> Client:  # pragma: nocover
    pass


def disconnect(client: Client, **kwargs):  # pragma: nocover
    pass


def publish(client: Client, **kwargs) -> Optional[Any]:  # pragma: nocover
    pass


def subscribe(client: Client, **kwargs) -> Iterator[Msg]:  # pragma: no cover
    pass
