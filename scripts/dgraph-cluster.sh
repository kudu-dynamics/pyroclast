#!/bin/sh
set -e

DGRAPH_VERSION="v1.1.0"
JAEGER_VERSION="1.6"

tmux new-session -d -s dgraph
tmux rename-window -t dgraph 'jaeger'
tmux send-keys -t dgraph "docker run --rm -it --net=host jaegertracing/all-in-one:${JAEGER_VERSION}" 'C-m'
tmux new-window -t dgraph
tmux rename-window -t dgraph 'dgraph'
tmux send-keys -t dgraph "docker run --rm -it --net=host dgraph/dgraph:${DGRAPH_VERSION} dgraph zero --telemetry=false --jaeger.collector=http://localhost:14268" 'C-m'
tmux split-window -t dgraph -h
tmux send-keys -t dgraph "docker run --rm -it --net=host dgraph/dgraph:${DGRAPH_VERSION} dgraph alpha --lru_mb=4096 --jaeger.collector=http://localhost:14268" 'C-m'
tmux setw synchronize-panes
tmux attach-session -t dgraph
