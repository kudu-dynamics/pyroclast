import os
from typing import Any, BinaryIO, Optional, Union

import boto3
from botocore.exceptions import ClientError

import pyroclast.common.kv as KV


# client interface


def connect(*args, **kwargs) -> KV.Client:
    """Connect to S3.

    Parameters
    ----------
    aws_access_key_id : str, optional
        Extracts from the environment variable "AWS_ACCESS_KEY_ID" by default.

    aws_secret_access_key : str, optional
        Extracts from the environment variable "AWS_SECRET_ACCESS_KEY" by default.

    endpoint_url : str, optional
    """
    aws_access_key_id = kwargs.get("aws_access_key_id", os.getenv("AWS_ACCESS_KEY_ID"))
    aws_secret_access_key = kwargs.get("aws_secret_access_key", os.getenv("AWS_SECRET_ACCESS_KEY"))
    endpoint_url = kwargs.get("endpoint_url", os.getenv("AWS_ENDPOINT_URL"))

    s3 = boto3.resource(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        endpoint_url=endpoint_url,
    )
    client = KV.Client(s3, name="s3")
    for sym in KV.Symbols:
        setattr(client, sym, globals()[sym].__get__(client))
    return client


# kv interface


def kv_get(client: KV.Client, bucket, key: str) -> Optional[BinaryIO]:
    s3 = client.raw_client
    bucket = s3.Bucket(name=bucket)
    try:
        return bucket.Object(key=key).get().get("Body", None)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return None
        raise


def kv_set(
    client: KV.Client, bucket: str, key: Optional[str] = None, data: Optional[Union[bytes, BinaryIO]] = None
) -> Any:
    """Set a key with S3 (either creates a bucket or an object).

    Parameters
    ----------
    bucket : str
        Name of the bucket to interact with.

    key : Optional[str]
        Name of the object to interact with.
        If set to None, creates a bucket instead of an object.

        Extracts from the environment variable "AWS_ACCESS_KEY_ID" by default.

    data : Optional[Union[bytes, BinaryIO]]
        Data can either be a bytes object or an IO bytes stream.
        If data is not set, a ValueError will be raised unless key is also
        unset. In that case, a bucket will be created.
    """
    s3 = client.raw_client

    if key is not None and data is not None:
        # Create Object.
        return s3.Object(bucket, key).put(Body=data)
    elif key is None and data is None:
        # Create Bucket.
        try:
            return s3.Bucket(bucket).create()
        except ClientError as e:
            if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
                return None
            raise
    else:
        raise ValueError("either `bucket`, `key`, and `data` must be set " "or only `bucket`")


def kv_pop(client: KV.Client, bucket, key: str) -> Any:
    s3 = client.raw_client
    return s3.Object(bucket, key).delete()
