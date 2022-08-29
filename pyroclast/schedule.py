import base64
from contextlib import suppress
from functools import partial
import json
import os
import socket
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import namesgenerator
from plexiglass.jot import Jot
import structlog as logging

from pyroclast.nomad_proxy import (
    Nomad,
    until_task_group_summary_count,
    is_under_running_children_count,
    until_under_running_children_count,
    wait_for_allocation_to_complete,
    wait_for_first_available_allocation,
)
from pyroclast.settings import configure
from pyroclast.utils import listify


_LOGGER = logging.getLogger(__name__)


# Default Nomad job scaffolding.
TaskGroup = Jot({
    "Name": "",
    "Tasks": [],
})
NoRepeatTaskGroup = TaskGroup({
    "ReschedulePolicy": {
        "Attempts": 0,
    },
    "RestartPolicy": {
        "Attempts": 0,
        "Mode": "fail",
    },
})
Job = Jot({
    "Job": {
        "Type": "service",
        "Priority": 50,
        # The most common default option is for datacenters to be "dc1".
        "Datacenters": ["dc1"],
        "Constraints": [],
    },
})
ParameterizedJob = Job({
    "Job": {
        "Type": "batch",
        "ParameterizedJob": {
            "Payload": "optional",
            "MetaRequired": [],
            "MetaOptional": [],
        },
        "TaskGroups": [NoRepeatTaskGroup],
    },
})
DockerTask = Jot({
    "Name": "",
    "Driver": "docker",
    "Config": {
        "image": "",
        "port_map": [],
        "volumes": [],
    },
    "Env": {},
    "Resources": {
        "Networks": [],
    },
})
ExecTask = Jot({
    "Name": "",
    "Driver": "exec",
    "Config": {
        "command": "",
        "args": [],
    },
})


def get_nomad_client_id():
    """
    Fingerprint the Nomad client that will be used for task localization.
    """
    # If this code is run as part of a Nomad job, use the running ALLOC_ID
    # to fingerprint the running Nomad client.
    alloc_id = os.getenv("NOMAD_ALLOC_ID", None)
    print(alloc_id)
    if alloc_id:
        return Nomad.get_allocation(alloc_id)["NodeID"]

    # If no client id can be found, try and match the host IP address to a
    # running client.
    with suppress(socket.error):
        addresses = socket.gethostbyname_ex(socket.gethostname())[-1]
        client_ids = dict((node["Address"], node["ID"]) for node in Nomad.get_nodes())
        for addr in set(client_ids.keys()) & set(addresses):
            return client_ids[addr]

    raise ValueError("Could not find a Nomad client to localize execution to.")


class Schedule:
    """
    Define the Nomad API.
    """
    @configure
    def register_driver_docker(self, job_name: str, image: str, **kwargs: Any) -> Dict[str, Any]:
        """Define a Nomad Parameterized Job using the Docker driver with some sane defaults.

        For more information about the potential keyword arguments,
        refer to the Nomad documentation.

        - https://www.nomadproject.io/docs/drivers/docker.html
        - https://www.nomadproject.io/docs/job-specification/index.html
        - https://www.nomadproject.io/api/json-jobs.html

        Parameters
        ----------
        job_name : str
            The name of the parameterized job to register.

        image : str
            The Docker image to use.

        args : List[str], optional
            A list of argument strings to pass to the Docker runtime.

        constraints : List[str], optional
            A list of job constraints for the Nomad parameterized job.

        entrypoint : List[str], optional
            A list of entrypoint strings to pass to the Docker runtime.

        environment : Dict[str, str], optional
            A set of environment variable key value pairs.

        job_type : str, optional
            The type of Nomad job to run.
            Defaults to "parameterized" but can also be "service" and "periodic".

        meta : List[str], optional
            A list of optional meta fields for the Nomad parameterized job.

        payload_filename : str, optional
            The default filename at which to serve input payload data to the
            Nomad parameterized job.
            Within the task filesystem, the file will be found at
            `/local/{payload_filename}`.

        ports : List[dict], optional
            Provide a list of port information dictionaries.
            These dictionaries should provide the keys: label, dest, host.
                The label is the name of the port to register.
                The dest value is the port within the container to map.
                The host value is the port on the host to map. Omit for a
                dynamically-allocated port.

        resources : Dict[str, str], optional
            The resources to allocate for each allocation of this Nomad
            parameterized job.
            e.g. `{"CPU": 1000, "MemoryMB": 1024}`

        volumes : List[str], optional
            A list of volume strings to pass to the Docker runtime.

        Returns
        -------
        dict
            A JSON-serializable dictionary conforming to the Nomad JSON Specification [0, 1, 2].
        """
        # Driver-specific parameters.
        args: List[str] = listify(kwargs.pop("args", []))
        constraints: List[str] = listify(kwargs.pop("constraints", []))
        entrypoint: List[str] = listify(kwargs.pop("entrypoint", []))
        environment: Dict[str, str] = kwargs.pop("environment", {})
        ports: List[dict] = listify(kwargs.pop("ports", []))
        resources: Dict[str, int] = kwargs.pop("resources", {})
        job_type: str = kwargs.pop("job_type", "parameterized")
        volumes: List[str] = listify(kwargs.pop("volumes", []))

        # The registered job will have one Docker task.
        task = DockerTask({
            "Name": job_name,
            "Config": {
                "image": image,
                "entrypoint": entrypoint,
                "args": args,
                "volumes": volumes,
            },
            "Env": environment,
            "Resources": resources,
        })
        for port in ports:
            try:
                label = port["label"]
            except KeyError:
                raise ValueError(f"A Docker Job port must have a 'label': {port}.")
            try:
                dest = port["dest"]
            except KeyError:
                raise ValueError(f"A Docker Job port must have a 'dest': {port}.")

            # Map the port in the Docker driver config.
            task.Config.port_map.append({label: int(dest)})

            network = Jot({
                "DynamicPorts": [],
                "ReservedPorts": [],
            })
            if "host" not in port:
                # Dynamic Port.
                network.DynamicPorts.append({"Label": label})
            else:
                # Static Port.
                network.ReservedPorts.append({"Label": label, "Value": str(port["host"])})

            if not task.Resources.Networks:
                task.Resources.Networks.append(network)
            else:
                for n in task.Resources.Networks:
                    n.merge(network)

        # Support 3 major styles of Nomad.
        # Parameterized
        # Periodic
        # Service
        if job_type == "parameterized":
            meta: List[str] = listify(kwargs.pop("meta", []))
            payload_filename: str = kwargs.pop("payload_filename", "input.txt")

            job = ParameterizedJob()
            # All forms of input to the parameterized job (meta fields and payload file)
            # will be optional to provide fluid use of the Nomad API.
            job.Job.ParameterizedJob.MetaOptional.extend(meta)
            task.DispatchPayload.File = payload_filename
        else:
            job = Job()
            job.Job.TaskGroups = [TaskGroup()]

        job.Job.ID = job_name
        job.Job.Name = job_name
        job.Job.Constraints = constraints
        job.Job.TaskGroups[0].Name = job_name
        job.Job.TaskGroups[0].Tasks.append(task)

        # Json loading the string representation of the job resolves intermediate
        # Python convenience objects.
        return json.loads(str(job))

    @configure
    def register(self,
                 name: Optional[str] = None,
                 client_id: Optional[str] = None,
                 constraints: List[str] = [],
                 driver: str = "docker",
                 localize: bool = True,
                 update: bool = True,
                 **kwargs: Any) -> Callable:
        """Registers a Nomad job and returns a function to run it.

        Provides a programmatic interface to create Nomad parameterized jobs
        that simplifies configuration and dispatch of execution primitives
        (e.g. containers, Java JARs, fork/exec processes, etc).

        For more information about the Nomad job specification,
        refer to the Nomad documentation.

        - https://www.nomadproject.io/docs/job-specification/index.html
        - https://www.nomadproject.io/api/json-jobs.html

        Parameters
        ----------
        name : Optional[str], optional
            The name of the parameterized job to register.

        client_id : Optional[str], optional
            The ID value of the Nomad node to localize the job to.
            If no value is provided, the library will attempt to fingerprint for
            a running Nomad node.

        constraints : List[str], optional
            A list of job constraints for the Nomad parameterized job.

        driver : str, optional
            The Nomad task driver to use. Defaults to "docker".

        localize : bool, optional
            If set, constrains the registered Nomad job to the specified `client_id`.

        update : bool, optional
            If set, overwrites the existing job definition if found.
            If not set, returns a partial to the existing job if it already exists.

        Returns
        -------
        Callable
            A partial capture of the dispatch function.

        See Also
        --------
        dispatch               : The method proxying the Nomad job dispatch API.
        register_driver_docker : The configuration options for the Docker task driver.

        Examples
        --------
        .. code-block:: python

            >>> import pyroclast
            >>> pc = pyroclast.Pyroclast()
            >>> func = pc.register(
            ...     image="busybox:latest",
            ...     entrypoint=["sh", "-c"],
            ...     args=["${NOMAD_META_args}"],
            ...     meta=["args"],
            ... )
            >>> try:
            ...     result = func(meta={"args": "ls -al"})
            ...     print(result.exit_code)
            ...     print(f"'{result.stdout}'")
            ...     print(f"'{result.stderr}'")
            ... finally:
            ...     func.close()
            0
            'alloc
            bin
            dev
            etc
            home
            local
            proc
            root
            secrets
            sys
            tmp
            usr
            var
            '
            ''
        """
        job_name: str = name or namesgenerator.get_random_name()

        if localize:
            client_id = client_id or get_nomad_client_id()
            if not any(client_id == n["ID"] for n in Nomad.get_nodes()):
                raise ValueError(f"Could not find Nomad client: {client_id}")

            # Make sure not to write to a default parameter.
            constraints = constraints[:]
            constraints.append({
                "LTarget": "${node.unique.id}",
                "RTarget": client_id,
                "Operand": "=",
            })
            job_name = f"{job_name}-{client_id}"

        # Register the job if it does not already exist.
        # If it does exist, register a new version only if the `update` flag is set.
        if update or not Nomad.has_job(job_name):
            if driver == "docker":
                job = self.register_driver_docker(
                    job_name,
                    constraints=constraints,
                    **kwargs,
                )
            else:
                raise ValueError(f"Pyroclast does not currently support driver '{driver}'.")

            Nomad.register_job(job_name, job)

        # Provide a single function to simplify the simplest direct use case.
        func = partial(self.run, job_name)
        setattr(func, "close", lambda: Nomad.deregister_job(job_name))
        return func

    @configure
    def dispatch(self,
                 job_name: str,
                 payload: Optional[str] = None,
                 meta: Dict[str, str] = {},
                 **kwargs: Any) -> Tuple[str]:
        """Dispatches a Nomad parameterized job.

        Handles a few behaviors related to dispatching jobs.

        Parameters
        ----------
        job_name : str
            The name of the parameterized job to dispatch.

        block_to_schedule: bool, optional
            If set to True, this method will block until there are enough
            resources available to run the job. Enabled by default.

        max_dispatch : int, optional
            The maximum number of concurrent allocations allowed to run for the
            given `job_name`. If not set, a maximum of 50 allocations will be
            run concurrently.

        max_only_pending: bool, optional
            If this flag is set, the limit only pertains to the number of
            pending allocations.

        Notes
        -----
        Although the `max_dispatch` parameter sets an upper bound for the number
        of concurrently running dispatched jobs, the value is not a strict upper
        bound without additional application-logic for distributed locking.

        Returns
        -------
        Tuple[str, str]
            The dispatched job id and its primary allocation id.
        """
        block_to_schedule: bool = bool(kwargs.pop("block_to_schedule", False))
        max_dispatch: int = int(kwargs.pop("max_dispatch", 50))
        max_only_pending: bool = bool(kwargs.pop("max_only_pending", False))

        if not Nomad.has_job(job_name):
            raise ValueError(f"{job_name} not registered in Nomad.")

        job = Nomad.get_job(job_name)

        if payload is not None:
            payload = base64.b64encode(payload.encode()).decode()

        # Wait for confirmation that the scheduling servers are considering our job.
        job_id = None
        # Wait until the number of running children is below the threshold.
        if block_to_schedule:
            until_under_running_children_count(job_name, max_dispatch, max_only_pending)
        elif not is_under_running_children_count(job_name, max_dispatch, max_only_pending):
            raise ValueError(f"not enough resources to dispatch {job_name}")

        # Dispatch the job if it is a parameterized job.
        if job["Type"] == "batch" and job["ParameterizedJob"]:
            job_id = Nomad.dispatch_job(job_name, meta=meta, payload=payload)["DispatchedJobID"]
        else:
            job_id = job_name

        # Wait until all task groups have acknowledged and scheduled an allocation.
        until_task_group_summary_count(job_id)

        # Once we have confirmed that an allocation in some state has
        # been issued by Nomad, we can look up the first available one and return its ID.
        allocation_id = wait_for_first_available_allocation(job_id)["ID"]
        return job_id, allocation_id

    @configure
    def wait(self, job_id: str, alloc_id: str, **kwargs: Any) -> Optional[Jot]:
        """Block until a Nomad job has either started, completed, or timed out.

        This method makes the assumption that the dispatch job in question has a
        policy of 0 restarts and 0 reschedules.
        Otherwise, an allocation would be considered complete in between being
        marked queued/starting between retries.

        Parameters
        ----------
        job_id : str
            The ID value of the dispatched parameterized job.

        alloc_id : str
            The string value of the Nomad allocation id.

        Examples
        --------
        .. code-block:: python
            >>> import pyroclast
            >>> pc = pyroclast.Pyroclast()
            >>> ...
            >>> result = pc.wait(f"{job_name}", f"{alloc_id}")
            >>> print(result.exit_code)
            0
            >>> print(f"'{result.stdout}'")
            ''
            >>> print(f"'{result.stderr}'")
            ''

        Returns
        -------
        Optional[Jot]
            A container object that stores useful attributes regarding the
            execution of a job.
        """
        result = Jot()

        # Avoid waiting on non-batch jobs which are not guaranteed to terminate.
        job = Nomad.get_job(job_id)
        if job["Type"] != "batch":
            return Jot(Nomad.get_allocation(alloc_id))

        allocation = wait_for_allocation_to_complete(alloc_id)

        # Get the exit code of the allocation.
        for task_name, state in allocation["TaskStates"].items():
            for event in state["Events"]:
                if event["Type"] == "Terminated":
                    details = event["Details"]
                    result.exit_code = int(details["exit_code"])
                    result.oom_killed = details["oom_killed"]
                    break
            # DEV: There should only be one task.
            break

        if "exit_code" not in result:
            raise ValueError("Could not determine the job exit_code.")

        # Get the log data from the allocation.
        result.stdout = Nomad.get_log(alloc_id, task_name, "stdout", plain=True)
        result.stderr = Nomad.get_log(alloc_id, task_name, "stderr", plain=True)
        return result

    @configure
    def run(self, job_name: str, **kwargs: Any) -> Dict[str, Any]:
        """Wrapper function that synchronously dispatches and returns results for a job.

        See Also
        --------
        dispatch : The method proxying the Nomad job dispatch API.
        wait     : The method to synchronously wait for the completion of a Nomad job.
        """
        return self.wait(*self.dispatch(job_name, **kwargs), **kwargs)

    @configure
    def get_nodes(self, **kwargs) -> Iterator[dict]:
        """Get all available Nomad nodes in the cluster.

        Parameters
        ----------
        count : int, optional
            The number of nodes to return.

        meta_whitelist : Dict[str, Optional[str]], optional
            A dictionary of meta keys and values used to find matching nodes.
            If the value is set to None, the presence of the key will be considered a match.

        meta_blacklist : Dict[str, Optional[str]], optional
            A dictionary of meta keys and values used to filter nodes.
            If the value is set to None, the presence of the key will be considered a match.

        Returns
        -------
        dict
            Return a dictionary containing node details.
        """
        count = int(kwargs.pop("count", 0))
        meta_whitelist = kwargs.pop("meta_whitelist", {})
        meta_blacklist = kwargs.pop("meta_blacklist", {})

        for node in Nomad.get_nodes():
            node_details = Nomad.get_node(node["ID"])
            if not meta_whitelist and not meta_blacklist:
                yield node_details
            meta = node_details["Meta"] or {}

            # Keys that have None values in the whitelist/blacklist
            # automatically set their value to the existing meta value to ensure
            # a match occurs.
            for key, value in meta.items():
                if key in meta_whitelist and meta_whitelist[key] is None:
                    meta_whitelist[key] = value
                if key in meta_blacklist and meta_blacklist[key] is None:
                    meta_blacklist[key] = value

            matches = set(meta.items()) & set(meta_whitelist.items()) - set(meta_blacklist.items())
            if matches:
                yield node_details

                # Only yield up to count nodes.
                count -= 1
                if count == 0:
                    break
