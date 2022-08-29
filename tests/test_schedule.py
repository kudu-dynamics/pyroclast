import os

import pytest
import requests
from tenacity import retry, stop_after_delay

import pyroclast


pytest.skip("skipping schedule subsystem", allow_module_level=True)
pytestmark = pytest.mark.skipif(not os.getenv("NOMAD_ADDR", None), reason="No available Nomad service.")


def test_basic():
    """
    Register a simple Docker parameterized task with busybox.
    """
    pc = pyroclast.Pyroclast()
    func = pc.register(
        image="busybox:latest",
        entrypoint=["sh", "-c"],
        args=["${NOMAD_META_args}"],
        meta=["args"],
    )
    try:
        result = func(meta={"args": "ls -al"})
        print(result)
        assert result.exit_code == 0
        assert "local" in result.stdout
        assert not result.stderr

        # Add a typo to cause an error.
        result = func(meta={"args": "ls-al"})
        assert result.exit_code != 0
    finally:
        func.close()


@pytest.mark.skip(reason="removed timeout handling")
def test_timeouts():
    """
    Test the conditions in which jobs take too long to schedule or
    take too long to run.
    """
    pc = pyroclast.Pyroclast()

    # Run against a job that has unreasonable memory constraints.
    # When the resource requirements are evaluated, the Nomad scheduler
    # will be unable to place the job and we will hit the `scheduling_timeout`.
    func = pc.register(
        image="busybox:latest",
        entrypoint=["sh", "-c"],
        args=["${NOMAD_META_args}"],
        meta=["args"],
        # Request that our job be allocated a petabyte of memory.
        resources={"MemoryMB": 1024 ** 3},
    )
    try:
        with pytest.raises(TimeoutError):
            func(meta={"args": "ls -al"}, scheduling_timeout=3)
    finally:
        func.close()

    # Run against a job that will be successfully scheduled, but in a way
    # that it will never successfully complete execution.
    func = pc.register(
        image="busybox:latest",
        entrypoint=["sh", "-c"],
        args=["${NOMAD_META_args}"],
        meta=["args"],
    )
    try:
        with pytest.raises(TimeoutError):
            func(meta={"args": "sleep infinity"}, timeout=3)
    finally:
        func.close()


def test_error_nonexistent_client():
    """
    Test the case in which a job is registered to a fictional client_id.
    """
    pc = pyroclast.Pyroclast()

    with pytest.raises(ValueError):
        pc.register(
            client_id="client_that_does_not_exist!",
            image="busybox:latest",
            entrypoint=["sh", "-c"],
            args=["${NOMAD_META_args}"],
            meta=["args"],
        )


def test_service():
    """
    Create a Docker-based service job.
    """
    pc = pyroclast.Pyroclast()

    try:
        func = pc.register(
            image="python:3.7-slim",
            entrypoint=["python", "-m", "http.server"],
            args=["8000"],
            job_type="service",
            localize=False,
            ports=[{"label": "http", "dest": 8000}],
            update=False,
        )
        alloc_info = func()
        resources = list(alloc_info.TaskResources.values())[0]
        ip = resources.Networks[0]["IP"]
        port = resources.Networks[0]["DynamicPorts"][0]["Value"]
        url = f"http://{ip}:{port}"

        @retry(stop=stop_after_delay(60))
        def get():
            return requests.get(url)

        response = get()
        assert "Directory listing" in response.text
    finally:
        func.close()
