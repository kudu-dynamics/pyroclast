import os

import pyroclast.data.redis as KV

client = KV.connect(host=os.getenv("REDIS_HOST", "localhost"))  # Normal port is 6379.

# The standard KV interface supports "get", "set", and "pop".

client.kv_pop("hello")

KV.kv_get(client, "hello")

KV.kv_set(client, "hello", "world")

client.kv_get("hello")

# All data clients from Pyroclast expose the underlying library for
# manual interaction.

r = client.raw_client
for key in r.scan_iter():
    print(key, r.get(key))
