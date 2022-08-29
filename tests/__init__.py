import os


_BACKENDS = []


def _get_backends():
    global _BACKENDS
    _BACKENDS.extend([backend.lower() for backend in os.getenv("TEST_BACKENDS", "").split(" ") if backend])
    if not _BACKENDS:
        _BACKENDS = ["all"]


def should_skip(backend):
    """Determine whether a test should be skipped or not.

    If the environment variable `TEST_BACKENDS` is unset or set to "all", all
    tests should be run.

    Otherwise, if a module's shortname is not in the space separated list,
    it should not be run.

    e.g.

    TEST_BACKENDS="all"

    TEST_BACKENDS="redis s3"

    TEST_BACKENDS="sonic"
    """
    if not _BACKENDS:
        _get_backends()
    if "all" in _BACKENDS:
        return False
    return backend.lower() not in _BACKENDS
