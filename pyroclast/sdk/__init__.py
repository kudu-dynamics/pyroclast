"""
# Message Format (JSON)

## Success

The outgoing message must specify whether or not the processor was successful.

"success": bool

---

## Source/Sink

The messages can optionally specify a source and a sink.

### Redis

"input": {"type": "redis", "name": str}

"output": {"type": "redis", "name": str, "value": bytes}

### S3

"input": {"type": "s3", "path": str}

"output": {"type": "s3", "path": str, "value": bytes}

---
"""
