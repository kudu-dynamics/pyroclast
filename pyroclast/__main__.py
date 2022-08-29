"""
Pyroclast
"""
import argparse
import sys

from plexiglass import argparse_config, dgraph_config, logging_config
import structlog as logging

from pyroclast import create_client


_LOGGER = logging.getLogger("pyroclast")


def get_parser() -> argparse.ArgumentParser:
    parser = argparse_config.make_parser("pyroclast", __doc__)
    dgraph_config.configure_parser(parser)
    logging_config.configure_parser(parser)
    return parser


def main() -> None:
    cli_args = get_parser().parse_args()
    logging_config.configure_logging(cli_args)

    client = create_client(cli_args, update_schema=True)
    print(client)
    return 0


if __name__ == "__main__":
    sys.exit(main())
