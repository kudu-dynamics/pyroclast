class AbstractClient:
    """
    The AbstractClient is a general wrapper structure for data clients with
    pre-existing client libraries.

    The raw client is preserved for the user to manipulate internals as necessary
    while otherwise providing convenience functions on top.
    """

    def __init__(self, raw_client, **kwargs):
        self.raw_client = raw_client
        self.meta = kwargs
