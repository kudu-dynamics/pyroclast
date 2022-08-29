from functools import partial

import nomad
from tenacity import (
    retry,
    retry_if_exception,
    retry_if_exception_type,
    retry_if_not_result,
    stop_after_attempt,
    wait_random,
    wait_random_exponential,
)


__all__ = [
    "Nomad",
    "until_task_group_summary_count",
    "is_under_running_children_count",
    "until_under_running_children_count",
    "wait_for_allocation_to_complete",
    "wait_for_first_available_allocation",
]


def check_exception(exc):
    """Check whether or not to retry from an exception.

    https://www.nomadproject.io/api/index.html

    > Individual API's will contain further documentation in the case that more
      specific response codes are returned but all clients should handle the
      following.

    > 200 and 204 as success codes.
    > 400 indicates a validation failure and if a parameter is modified in the
      request, it could potentially succeed.
    > 403 marks that the client isn't authenticated for the request.
    > 404 indicates an unknown resource.
    > 5xx means that the client should not expect the request to succeed if
      retried.
    """
    if not isinstance(exc, nomad.api.exceptions.BaseNomadException):
        return False
    if not exc.nomad_resp:
        return False
    status_code = int(exc.nomad_resp.status_code)
    if status_code in (400, 403, 404):
        return False
    if 500 <= status_code < 600:
        return False
    print(exc.nomad_resp.status_code)
    print(exc.nomad_resp.text)
    return True


class Nomad:
    """The Nomad Proxy class provides default retry capabilities for resiliency.

    Occasionally, Nomad endpoints will return errors that are safe to retry for.
    By wrapping the most common Nomad API endpoints, we ensure that they are
    invoked durably to provide less burden to the application developer.
    """

    initialized = False
    proxy_methods = {
        "get_job": "nomad.Nomad().job.get_job",
        "has_job": "lambda job_name, *a, **kw: job_name in nomad.Nomad().jobs",
        "register_job": "nomad.Nomad().job.register_job",
        "deregister_job": "nomad.Nomad().job.deregister_job",
        "dispatch_job": "nomad.Nomad().job.dispatch_job",
        "summarize_job": "nomad.Nomad().job.get_summary",
        "get_allocation": "nomad.Nomad().allocation.get_allocation",
        "get_allocations": "nomad.Nomad().job.get_allocations",
        "stop_allocation": "nomad.Nomad().allocations.stop",
        "get_node": "nomad.Nomad().node.get_node",
        "get_nodes": "nomad.Nomad().nodes.get_nodes",
        "get_log": "nomad.Nomad().client.stream_logs.stream",
    }


def is_under_running_children_count(job_name: str, max_dispatch: int, max_only_pending: bool) -> bool:
    """Check if a Nomad job (`job_name`) has fewer running children than `max_dispatch`.

    Parameters
    ----------
    job_name : str
        The name of the parameterized job to dispatch.

    max_dispatch : int
        The maximum number of concurrent allocations allowed to run for the
        given `job_name`. If not set, a maximum of 50 allocations will be
        run concurrently.

    max_only_pending: bool, optional
        If this flag is set, the limit only pertains to the number of
        pending allocations.

    Returns
    -------
    bool
        Return whether or not the job is under the threshold.
    """
    summary = Nomad.summarize_job(job_name)
    children = summary["Children"]
    if not children:
        return False
    running_count = 0
    running_count += children["Pending"]
    if not max_only_pending:
        running_count += children["Running"]
    return running_count < max_dispatch


@retry(retry=retry_if_not_result(lambda v: v), wait=wait_random_exponential(max=60))
def until_under_running_children_count(*args, **kwargs) -> bool:
    """Block until a Nomad job's running count is under a certain threshold.

    Returns
    -------
    bool
        Stop retrying if the result is True.
    """
    return is_under_running_children_count(*args, **kwargs)


@retry(retry=retry_if_not_result(lambda v: v), wait=wait_random(0, 3))
def until_task_group_summary_count(job_id: str) -> bool:
    """Ensure that all task groups for Nomad job (`job_id`) have a tracked allocation.

    Parameters
    ----------
    job_id : str
        The ID value of the dispatched parameterized job.

    Notes
    -----
    The Nomad TaskGroupSummary struct is as follows.

        type TaskGroupSummary struct {
            Queued   int
            Complete int
            Failed   int
            Running  int
            Starting int
            Lost     int
        }

    Returns
    -------
    bool
        Stop retrying if the result is True.
    """
    summaries = Nomad.summarize_job(job_id)["Summary"]
    return all(sum(summary.values()) for summary in summaries.values())


@retry(retry=retry_if_exception_type(IndexError), wait=wait_random(0, 3))
def wait_for_first_available_allocation(job_id: str) -> dict:
    """Wait until the first available allocation for the given `job_id` is available.

    Parameters
    ----------
    job_id : str
        The ID value of the dispatched parameterized job.

    Returns
    -------
    dict
        The retrieved allocation data.
    """
    # DEV: The allocations are sorted in alphabetical order.
    #      Get the most recent one instead.
    allocations = sorted(Nomad.get_allocations(job_id), key=lambda a: -a["CreateIndex"])
    return allocations[0]


@retry(retry=retry_if_exception_type(KeyError), wait=wait_random(0, 3))
def wait_for_allocation_to_complete(alloc_id: str) -> dict:
    """Wait until the given allocation has completed.

    Parameters
    ----------
    alloc_id : str
        The ID value of an allocation.

    Returns
    -------
    dict
        The retrieved allocation data.
    """
    allocation = Nomad.get_allocation(alloc_id)
    return {"complete": allocation, "failed": allocation}[allocation["ClientStatus"]]


if not Nomad.initialized:

    @retry(retry=retry_if_exception(check_exception), stop=stop_after_attempt(10), wait=wait_random_exponential(max=60))
    def wrapper(method, *a, **kw):
        return eval(method)(*a, **kw)

    for name, method in Nomad.proxy_methods.items():
        setattr(Nomad, name, staticmethod(partial(wrapper, method)))

    Nomad.initialized = True
