"""
Provide a synchronous NATS/STAN client.

The currently forecasted usecases are as follows.

1. FastAPI publisher: enqueue as requests arrive (201 Created).
2. Single-threaded listener: perform IO work for incoming messages.

## Thread Safety

Similar to the github.com/dpkp/kafka-python package, the producer in this package
is most likely safe to be used across threads, but the consumer should not be.

## Message Queue Semantics

### At most once delivery


### At least once delivery
"""
import argparse
from contextlib import suppress
import json
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Type

import nats.aio.client as NATS
import nats.aio.errors
import stan.aio.client as STAN
import structlog as logging
from plexiglass.time import Timeout

from pyroclast.common.asyncio import sync_await
import pyroclast.common.queue as Q


_LOGGER = logging.getLogger(__name__)


# config management


def _kw_get(key: str, kw_type: Type, kwargs, **_kwargs) -> Any:
    strict = _kwargs.get("strict", True)

    if key in kwargs:
        value = kwargs[key]
        if strict and not isinstance(value, kw_type):
            raise ValueError(f"expected keyword argument `{key}: {kw_type}`, " f"instead got `{key}: {type(value)}`")
        return value
    elif "default" in _kwargs:
        return _kwargs["default"]
    else:
        raise ValueError(f"keyword argument `{key}: {kw_type}` must be provided")


def _kw_get_urls(kwargs) -> List[str]:
    result = []
    if "url" in kwargs:
        result.append(_kw_get("url", str, kwargs))
    result.extend(_kw_get("urls", list, kwargs, default=[]))
    if not result:
        raise ValueError("`url` or `urls` must be provided as keyword arguments")
    return result


def _kw_get_stan_connect_options(kwargs) -> Optional[Tuple[str, str]]:
    client_id = _kw_get("client_id", str, kwargs, default=None)
    cluster_id = _kw_get("cluster_id", str, kwargs, default=None)
    if client_id is not None and cluster_id is not None:
        # Valid connection settings were passed in.
        return client_id, cluster_id
    elif client_id is None and cluster_id is None:
        # No attempt was made to provide stan connection settings.
        return None
    else:
        # Partial settings were given, implying a desire to provide STAN
        # connection settings. Raise an error.
        raise ValueError("`client_id` and `cluster_id` must be provided as keyword arguments")


def _kw_get_count(kwargs) -> Optional[int]:
    result = _kw_get("count", int, kwargs, default=None)
    if isinstance(result, int) and result <= 0:
        raise ValueError("keyword argument `count` must be greater than 0 " "if provided")
    return result


def _kw_get_stan_sub_options(kwargs) -> Dict:
    result = _kw_get("sub_opts", dict, kwargs, default={})
    durable_name = _kw_get("durable_name", str, result, default=None)
    manual_acks = _kw_get("manual_acks", bool, result, default=False)
    # Durable Name implies manual_ack.
    if durable_name is not None or manual_acks:
        result["max_inflight"] = 1
        result["manual_acks"] = True
    return result


# client interface


def connect(**kwargs) -> Q.Client:
    """Connect to NATS/STAN server(s).

    Parameters
    ----------
    url : str
        The url string of a server (e.g. nats://127.0.0.1:4222).
        At least one url must be provided with `url` or `urls`.
    urls : List[str]
        A list of server url strings.
        At least one url must be provided with `url` or `urls`.
    """
    # Options
    stan_conn_opts = _kw_get_stan_connect_options(kwargs)
    urls = _kw_get_urls(kwargs)

    nc = NATS.Client()
    sync_await(nc.connect(servers=urls))

    if stan_conn_opts is not None:
        sc = STAN.Client()
        client_id, cluster_id = stan_conn_opts
        sync_await(sc.connect(client_id=client_id, cluster_id=cluster_id, nats=nc))
    else:
        sc = None
    # Make convenience bindings for the client.
    client = Q.Client(name="nats", raw_client=[nc, sc])
    if stan_conn_opts is not None:
        # Provide the ability for the client to manually ack.
        setattr(client, "ack", ack.__get__(client))
    setattr(client, "disconnect", disconnect.__get__(client))
    setattr(client, "publish", publish.__get__(client))
    setattr(client, "subscribe", subscribe.__get__(client))
    setattr(client, "is_connected", is_connected.__get__(client))
    setattr(client, "request", request.__get__(client))
    return client


def ack(client: Q.Client, message: NATS.Msg) -> Any:
    # XXX: Determine the appropriate return type.
    _, sc = client.raw_client
    if sc is not None:
        return sync_await(sc.ack(message))


def is_connected(client: Q.Client) -> bool:
    nc, _ = client.raw_client
    return nc.is_connected


def disconnect(client: Q.Client, **kwargs):
    nc, sc = client.raw_client
    if sc is not None:
        sync_await(sc.close())
    if not nc.is_closed:
        sync_await(nc.close())


def publish(client: Q.Client, **kwargs):
    channel = _kw_get("channel", str, kwargs)
    data = _kw_get("data", bytes, kwargs)

    nc, sc = client.raw_client
    if sc is not None:
        return sync_await(sc.publish(channel, data))
    else:
        return sync_await(nc.publish(channel, data))


def subscribe(client: Q.Client, **kwargs) -> Iterator[NATS.Msg]:  # noqa: C901
    """Subscribe to a NATS/STAN channel and receive messages off the wire.

    NATS Streaming subscriptions have a diverse set of flags and tunable
    semantics. Refer to the documentation for more information.

    - https://nats-io.github.io/docs/developer/streaming/receiving.html
    - https://nats-io.github.io/docs/developer/streaming/durables.html
    - https://nats-io.github.io/docs/developer/streaming/queues.html

    Parameters
    ----------
    client : Q.Client
        Provide a client wrapper that was generated from `connect`.
    channel : str
        The name of the NATS Streaming channel to subscribe to.
    auto_unsubscribe : bool, optional
        When set to True, unsubscribe automatically from the channel.
        This has a specific semantic with NATS Streaming to clear the channel
        when no subscribers remain.
    blocking : bool, optional
        When set to False, the subscribe iterator will return None values each
        time a sleep would otherwise have been invoked.
    count : Optional[int], optional
        When set to None, continue to listen to messages until interrupted.
        Otherwise, listen for a set `count` number of messages before stopping.
    sub_opts : dict, optional
        Settings for the underlying `stan.aio.client.Client().subscribe` call.
    timeout : Optional[int], optional
        When set to None, listen continuously.
        Otherwise, listen for a maximum of `timeout` seconds.

    Yields
    ------
    Iterator[nats.aio.client.Msg]
        A NATS.Msg object for each message received from the open subscription.
    """
    # Options
    auto_unsubscribe = _kw_get("auto_unsubscribe", bool, kwargs, default=False)
    blocking = _kw_get("blocking", bool, kwargs, default=True)
    channel = _kw_get("channel", str, kwargs)
    count = _kw_get_count(kwargs)
    sub_opts = _kw_get_stan_sub_options(kwargs)
    timeout = _kw_get("timeout", int, kwargs, default=None)

    # Variables
    nc, sc = client.raw_client
    cc = sc if sc is not None else nc

    sub = None
    done = False
    messages = []

    async def cb(msg):
        # XXX: Handle exceptions in the callback.
        nonlocal count
        nonlocal done

        if done:  # pragma: no cover
            return

        # Clients using `manual_acks` must ack messages or risk being redelivered
        # the same message in perpetuity.
        messages.append(msg)
        if isinstance(count, int):
            count -= 1
            if count <= 0:
                done = True

    sub = sync_await(cc.subscribe(channel, cb=cb, **sub_opts))

    try:
        with Timeout(timeout):
            while messages or not done or not nc.is_connected:
                if not messages:
                    if not blocking:
                        yield None
                    else:
                        # DEV: Resolution dependent on the OS.
                        time.sleep(1 / 60)
                for message in messages:
                    yield message
                messages.clear()
    except TimeoutError:
        # Ignore timeouts.
        pass
    finally:
        if sub is not None and not isinstance(sub, int):
            # The sub return from nc.subscribe is an sid int value.
            if auto_unsubscribe:
                sync_await(sub.unsubscribe())
            else:
                sync_await(sub.close())


def request(client: Q.Client, subject: str, payload: bytes, **kwargs) -> NATS.Msg:
    nc, _ = client.raw_client
    return sync_await(nc.request(subject, payload, **kwargs))


# pyroclast sdk


def listen(cli_args: argparse.Namespace, handler: Callable, **kwargs):  # noqa: C901
    """
    Connects to a NATS server and subscribes to messages from a channel.
    """
    result = 0

    # Set up the subscription options.
    sub_opts = {}
    if kwargs.get("queue", False):
        sub_opts["queue"] = "workers"

    # Validate the settings.
    try:
        if not cli_args.nats_host or not cli_args.nats_channel:
            raise AttributeError()
    except AttributeError:
        raise ValueError(f"{__name__}: error: the following arguments are required: nats-host, nats-channel")

    # Connect to the server and begin consuming from the subscription.
    try:
        _LOGGER.info("connecting to NATS server", server=cli_args.nats_server)
        client = connect(url=cli_args.nats_server)
        _LOGGER.info("opening subscription", channel=cli_args.nats_channel)
        for message in client.subscribe(channel=cli_args.nats_channel, sub_opts=sub_opts):
            _LOGGER.debug(f"received message", size=len(message.data))
            response = {"success": False}
            try:
                data = json.loads(message.data.decode())
                # XXX: Validate the incoming message.
                response.update(handler(cli_args, data))
                # XXX: Validate the outgoing message.
            except KeyboardInterrupt:
                # Allow for analytics to quit and force a restart.
                raise
            except:
                _LOGGER.exception("could not handle message")
                # XXX: Reply to message that the job could not be launched.
            finally:
                # Send a reply to notify the client of success, ignoring failure
                # in cases where clients don't need a response.
                with suppress(nats.aio.errors.ErrBadSubject):
                    client.publish(channel=message.reply, data=json.dumps(response).encode())
    except:
        _LOGGER.exception(f"{__name__} exception")
        result = 1
    finally:
        # Disconnect on a best-effort basis.
        with suppress(Exception):
            _LOGGER.info("disconnecting from NATS server", server=cli_args.nats_server)
            client.disconnect()
        return result
