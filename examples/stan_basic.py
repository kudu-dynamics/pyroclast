# DEV: Ensure that you are connecting to a NATS Streaming server.
#      https://docs.nats.io/developing-with-nats-streaming/connecting

import pyroclast.data.nats as Q

client = Q.connect(
    url="nats://localhost:12345", cluster_id="test-cluster", client_id="client-pyro"  # Normal port is 4222.
)

Q.publish(client, channel="single-message", data="Hello World from Pyroclast!".encode())

# Subscribe for a single message.
# Specify the channel start at the beginning.
# The message published above should be received.
for msg in Q.subscribe(client, channel="single-message", count=1, sub_opts={"deliver_all_available": True}):
    print(f"{msg.seq}: {msg.data.decode()}")

Q.disconnect(client)
