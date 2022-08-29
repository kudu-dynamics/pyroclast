"""
As a note of context, wherever there is a `get_uuid` call, it is used to
deconflict persistent channels to ensure that we do not accidentally receive
data that was generated for a different test.
"""
import os

from plexiglass.uuid import get_uuid
import pytest

import pyroclast.data.nats as Q
from tests import should_skip


pytestmark = pytest.mark.skipif(should_skip("nats"), reason=f"flag set to skip {__name__}")


HOST = os.getenv("STAN_HOST", "127.0.0.1")
PORT = os.getenv("STAN_PORT", "4222")


def test_stan_deliver_all():
    """
    Connect to a NATS-Streaming server and publish a single message and
    subscribe to receive all stored messages.

    "I am new and want to read the entire history of the stream"
    """
    channel = get_uuid()

    client = Q.connect(url=f"nats://{HOST}:{PORT}", cluster_id="test-cluster", client_id="client-pyro")
    Q.publish(client, channel=channel, data="Hello STAN from Pyroclast!".encode())
    messages = []
    messages.extend(
        Q.subscribe(
            client, channel=channel, count=1, sub_opts={"deliver_all_available": True}, auto_unsubscribe=True, timeout=1
        )
    )
    assert len(messages) == 1
    assert messages[0].data.decode() == "Hello STAN from Pyroclast!"
    Q.disconnect(client)


def test_nats_basic():
    """
    Re-perform the same test as in the stan case, but show that the queue is only
    online for actively-listening consumers.

    "I just want to receive messages of a stream"
    """
    channel = get_uuid()

    client = Q.connect(url=f"nats://{HOST}:{PORT}")
    Q.publish(client, channel=channel, data="Hello NATS from Pyroclast!".encode())
    messages = []
    messages.extend(Q.subscribe(client, channel=channel, count=1, timeout=1))
    assert len(messages) == 0

    Q.disconnect(client)


def test_stan_error_ack():
    """
    If clients do not ack messages in manual_ack mode, they will receive the same
    message over and over.
    """
    channel = get_uuid()
    data = "Hello STAN from Pyroclast!"

    client = Q.connect(url=f"nats://{HOST}:{PORT}", client_id="client-pyro", cluster_id="test-cluster")
    # There should be 3 messages.
    client.publish(channel=channel, data=data.encode())
    client.publish(channel=channel, data=data.encode())
    client.publish(channel=channel, data=data.encode())
    # Force unacknowledged acks to cause resends in 1 second rather than 30 seconds.
    messages = list(
        client.subscribe(
            channel=channel,
            count=3,
            sub_opts={"ack_wait": 1, "deliver_all_available": True, "manual_acks": True},
            timeout=8,
        )
    )
    client.disconnect()
    assert len(messages) == 3
    assert len(set([message.seq for message in messages])) == 1

    client = Q.connect(url=f"nats://{HOST}:{PORT}", client_id="client-pyro", cluster_id="test-cluster")
    # If messages are properly acked, they will be returned in proper order.
    messages = []
    for message in client.subscribe(
        channel=channel,
        count=3,
        sub_opts={"ack_wait": 1, "deliver_all_available": True, "manual_acks": True},
        timeout=8,
    ):
        messages.append(message)
        client.ack(message)
    client.disconnect()
    assert len(messages) == 3
    assert len(set([message.seq for message in messages])) == 3


def test_stan_durable():
    """
    Publish to a channel and then disconnect.
    Reconnect and show that the next message was delivered.

    "I want to pick up where I left off in case I disconnect"
    """
    channel = get_uuid()
    data = "Hello STAN from Pyroclast!"
    other_data = data.replace("Hello", "Hello again")
    seq = None

    try:
        c_pub = Q.connect(url=f"nats://{HOST}:{PORT}", cluster_id="test-cluster", client_id="client-pyro-pub")
        c_sub = Q.connect(url=f"nats://{HOST}:{PORT}", cluster_id="test-cluster", client_id="client-pyro-sub")

        c_pub.publish(channel=channel, data=data.encode())

        messages = c_sub.subscribe(channel=channel, sub_opts={"durable_name": "i-remember"}, blocking=False)
        # The first message should be a None as we did not provide the
        # "deliver_all_available" setting.
        assert next(messages) is None

        c_pub.publish(channel=channel, data=data.encode())

        # Confirm that the subscriber is receiving messages.
        msg = next(messages)
        seq = msg.seq
        assert msg.data.decode() == data
        c_sub.ack(msg)

        # Have the subscriber disconnect and publish two messages while the
        # subscriber is offline.
        c_sub.disconnect()
        c_pub.publish(channel=channel, data=other_data.encode())
        c_pub.publish(channel=channel, data=other_data.encode())

        # Once the subscriber comes back online, assert that we are only
        # receiving the messages that we missed.
        c_sub = Q.connect(url=f"nats://{HOST}:{PORT}", cluster_id="test-cluster", client_id="client-pyro-sub")
        messages = c_sub.subscribe(channel=channel, sub_opts={"durable_name": "i-remember"}, count=2, timeout=2)
        count = 0
        for message in messages:
            count += 1
            assert message.data.decode() == other_data
            # Additionally, demonstrate that we are receiving messages in order.
            # This is done by implicitly setting the `max_inflight` setting to
            # 1 and having `manual_acks` enabled.
            assert message.seq == seq + 1
            seq = message.seq
            c_sub.ack(message)
        assert count == 2
    finally:
        c_pub.disconnect()
        c_sub.disconnect()


def test_stan_exactly_once():
    pass


def test_stan_queue():
    pass


def test_stan_connect_error():
    with pytest.raises(ValueError):
        # Missing required `url`/`urls` keyword arguments.
        client = Q.connect()

    with pytest.raises(ValueError):
        # Incorrect typing for the `url` keyword argument.
        client = Q.connect(url=5)

    with pytest.raises(ValueError):
        # Partial STAN configuration provided, missing required `client_id`.
        client = Q.connect(url=f"nats://{HOST}:{PORT}", cluster_id="test-cluster")

    with pytest.raises(ValueError):
        # Count cannot be `<=` 0.
        client = Q.connect(url=f"nats://{HOST}:{PORT}")
        next(Q.subscribe(client, channel="test", blocking=False, count=0))

    with pytest.raises(ValueError):
        # Missing a required `channel` keyword argument for publish.
        client = Q.connect(url=f"nats://{HOST}:{PORT}")
        Q.publish(client, data="Hello World!".encode())
