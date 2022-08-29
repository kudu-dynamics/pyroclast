"""

## Downloading pre-requisite tools.

- install Go (https://golang.org/doc/install)
- ensure `${GOPATH}` is set
- ensure `${GOPATH}/bin` is added to the `${PATH}` environment variable

Download the following 2 utilities.

```
$ go get github.com/nats-io/nats-streaming-server

$ go get github.com/nats-io/nats.go/examples/nats-pub
```

## Running the example.

```
terminal 1 $ nats-streaming-server

terminal 2 $ python examples/nats_consumer.py -vv --nats-host 127.0.0.1 --nats-channel test

terminal 3 $ nats-pub test '{"hello": "world"}'
```

"""
import argparse
import sys
from typing import Dict

from plexiglass import argparse_config, logging_config, nats_config
import pyroclast.data.nats as Q


def handler(cli_args: argparse.Namespace, data: Dict) -> Dict:
    print(f"received: {data}")
    return {"success": True}


def parse_args(argv=None):
    # Create a parser and add appropriate arguments to it.
    parser = argparse_config.make_parser(__name__, description=__doc__)
    logging_config.configure_parser(parser)
    nats_config.configure_parser(parser)

    # Parse the arguments.
    cli_args = parser.parse_args(argv)
    logging_config.configure_logging(cli_args)
    nats_config.configure_nats(cli_args)

    return cli_args


def main(argv=None):
    cli_args = parse_args(argv)
    return Q.listen(cli_args, handler, queue=True)


if __name__ == "__main__":
    __name__ = "nats_consumer"
    sys.exit(main())
