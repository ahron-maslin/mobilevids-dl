"""Command line parsing and logging setup."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from mobilevids import __PKGNAME__, __VERSION__

from .define import DEFAULT_SEGMENTS, DOWNLOAD_DIRECTORY, ENV_PASSWORD, ENV_USERNAME


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    parser = argparse.ArgumentParser(
        prog="mobilevids-dl",
        description="Mobilevids Downloader script",
        epilog=(
            f"Credentials are read from --username/--password, then the "
            f"{ENV_USERNAME}/{ENV_PASSWORD} environment variables, then the netrc file. "
            "Prefer the environment variables: arguments are visible to other "
            "users in the process list and are saved in your shell history."
        ),
    )

    parser.add_argument("search", nargs="?", help="title to search for")
    parser.add_argument("--version", action="version", version=f"{__PKGNAME__} {__VERSION__}")
    parser.add_argument("-a", "--ascii", action="store_true", help="show ascii art")
    parser.add_argument("-d", "--debug", action="store_true", help="enable debug logging")
    parser.add_argument("-i", "--info", action="store_true", help="show info about movie/show")
    parser.add_argument(
        "-e",
        "--episode",
        help="download a single episode (requires -t [TV ID] and -s [SEASON])",
    )
    parser.add_argument("-m", "--movie", help="ID of a movie to download")
    parser.add_argument(
        "-n",
        "--netrc",
        nargs="?",
        const=True,
        default=None,
        metavar="PATH",
        help="read credentials from a netrc file, using the default location if PATH is omitted",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DOWNLOAD_DIRECTORY,
        metavar="DIR",
        help=f"directory to save downloads in (default: {DOWNLOAD_DIRECTORY})",
    )
    parser.add_argument("-p", "--password", help="Mobilevids password")
    parser.add_argument(
        "--segments",
        type=int,
        default=DEFAULT_SEGMENTS,
        help=f"parallel connections per download (default: {DEFAULT_SEGMENTS})",
    )
    parser.add_argument("-s", "--season", help="season to download (requires -t)")
    parser.add_argument("-t", "--tv", help="ID of a TV show to download")
    parser.add_argument("-u", "--username", help="Mobilevids username")
    return parser


def configure_logging(debug: bool) -> None:
    """Send log records to the console at the requested verbosity."""
    if debug:
        logging.basicConfig(
            level=logging.DEBUG, force=True, format="%(name)s[%(funcName)s] %(message)s"
        )
    else:
        logging.basicConfig(level=logging.INFO, force=True, format="%(message)s")


def options_parser(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse ``argv``, validate flag combinations and configure logging."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # argparse cannot express these dependencies, so they are checked here
    # instead of being silently ignored at dispatch time.
    if args.episode and not (args.tv and args.season):
        parser.error("-e/--episode requires both -t/--tv and -s/--season")
    if args.season and not args.tv:
        parser.error("-s/--season requires -t/--tv")
    if args.segments < 1:
        parser.error("--segments must be at least 1")

    configure_logging(args.debug)
    # Never log args directly: it would include --password.
    logging.getLogger(__name__).debug(
        "Program arguments %s", {k: v for k, v in vars(args).items() if k != "password"}
    )
    return args
