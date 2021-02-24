"""Utilities used to mock other objects."""

from urllib3 import connectionpool, poolmanager


def patch_http_connection_pool(**constructor_kwargs):
    """This allows to override the default parameters of the HTTPConnectionPool constructor.

    For example, to increase the poolsize to fix problems
    with "HttpConnectionPool is full, discarding connection"
    call this function with maxsize=16 (or whatever size
    you want to give to the connection pool)

    Args:
      **constructor_kwargs:
    """

    class MyHTTPConnectionPool(connectionpool.HTTPConnectionPool):
        """Class to increase the size of the HTTP Connection pool."""

        def __init__(self, *args, **kwargs):
            """Initialize the HTTP Connection pool."""
            kwargs.update(constructor_kwargs)
            super().__init__(*args, **kwargs)

    poolmanager.pool_classes_by_scheme["http"] = MyHTTPConnectionPool
