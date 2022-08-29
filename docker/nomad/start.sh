#!/bin/sh
set -e

if [ "x${1}" = "x" ]; then
  echo "nomad.sh {data_dir}"
  exit 1
fi

nomad agent -bind=0.0.0.0 -client -data-dir="$1" -server --bootstrap-expect=1
