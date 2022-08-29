# Changelog

## Unreleased

### Todo
- backpressure: manage Nomad bin-packing by watching for backpressure signals
- dispatch: automatically watch lifecycle for Nomad dispatch jobs
- fairness: allow lower priority jobs to execute
- task.connect: dgraph_retry allow time-based retry policy
- task.task: pop_task multiple tasks
- task.task: pop_task must be able to pop available tasks from lower
             priority jobs
- task.task: limit the number of concurrent tasks a job can run

## v0.1.1 - Unreleased

### Added
- kv: added disconnect to expected api
- nats: listen wrapper
- nats: allow for hooks to interrupt execution with a KeyboardInterrupt
- schedule: add `max_only_pending` flag
- sonic: added KV backend

### Changed
- changed test fixtures to run based on the `TEST_BACKENDS` envvar.

## v0.1.0 - 2019-12-04

Complete redesign with careful considerations to the ergonomics of the various
Pyroclast subsystems. Initial focus has been mostly on the schedule API.

The goal is to now provide distilled expert knowledge when using the integrated
3rd-party technologies.

### Added
- poetry: packaging is managed by poetry
- pyroclast: main API is provided by a single object `pyroclast.Pyroclast()`
- sphinx: documentation generation is configured
- task.task: requeue_task
- tenacity: library that handles complex retry strategies
- queue: subsystem supporting NATS and STAN as brokers
- kv: subsystem supporting Redis and S3 backends

### Removed
- docker: no longer builds a Docker image, only provides a library
- utils (various): argparse, logging, jot, etc have been moved to plexiglass

## v0.0.4 - 2019-05-08
Dependent on a panic fix in Dgraph. The pop_task query can crash an Alpha instance.
https://github.com/dgraph-io/dgraph/issues/3201

Mandate working with only Dgraph v1.0.11, the last safe release.

### Added
- task.connect: handle issues with leader connections
- task.connect: allow configurable dgraph_retry by count
- task.job: separate methods handling jobs
- task.taskqueue: add new taskqueue node type
- utils: timer decorator

### Changed
- Dockerfile: debian base instead of alpine
  https://github.com/docker-library/docs/issuess/904
- task: call all auto method binding routines at the __init__.py level
- task.crud: support dot separated predicates
- task.taskqueue: fairness at same job priority level
- task.schema: reasons are now trigram indexed
- task.schema: all predicates use dots for separation over underscores
- task.schema: lock is now modified

### Removed
- task.crud: remove compile_query

## v0.0.3 - 2019-04-18
Address bottlenecks in the 0.0.2 release.

### Added
- task.connect: handle bad value variable query
- task.crud: compile_query, strip out comments and whitespace from queries
- task.task: initial attempt for fairness with pop_task
- task.task: batched task creation
- utils: add datetime shortcut

### Changed
- task.crud: allow get_by to get falsy values
- task.schema: remove unused indices and change task_name to exact
- task.task: overhaul pop_task query
- task.task: task_lock is present until the task succeeds/fails
- task.task: task order LIFO and FIFO supported naturally, document

## v0.0.2 - 2019-04-10

### Added
- task.connect: support when an expand(_all_) returns an unknown grpc error
- task.schema: use hash over exact for better indexing of some predicates
- task.schema: add support for an task_owner predicate
- task.schema: add start and finish time predicates
- task.task: add support for conveniently creating/popping tasks by owner
- task.task: add support for more task lifecycle functions
- tests: add more unit tests: specifically task lifecycle ones
- utils.uuid: create uuid usable for identification

### Changed
- task.connect: retry properly raises error if too many aborts happen

## v0.0.1 - 2019-04-09

### Added
- jot: post initial jot module with some tests
- task: transparent batching of Dgraph mutations with DgraphAutoTxn
- task: wrap pydgraph interfaces with Auto versions
- task: pydgraph interfaces are made pythonic (classes, context managers)
- task: crud autogenerates functions for a given schema
- task: add dgraph configuration arguments to parser
- task: add a decorator to automatically retry work when AbortedErrors occur
- task.crud: provide public interface to autogenerate for user schemas
