"""Program entry point: wires the CLI to the downloader and reports failures."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
from pathlib import Path

from mobilevids import __VERSION__

from .define import NOTIFY_ALERT
from .download import DownloadInterrupted
from .downloader import Downloader
from .errors import MobileVidsError
from .network import get_creds, session_init
from .options import options_parser

log = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_INTERRUPTED = 128 + int(signal.SIGINT)


def run(args: argparse.Namespace, downloader: Downloader) -> None:
    """Invoke the action selected by the command line flags."""
    if args.search:
        downloader.search(args.search)
    elif args.movie:
        downloader.get_movie_by_id(args.movie)
    elif args.tv:
        if args.episode:
            downloader.get_single_episode(args.tv, args.season, args.episode)
        else:
            downloader.get_show_by_id(args.tv, args.season)
    else:
        downloader.search()


def main(argv: list[str] | None = None) -> int:
    """Run the downloader and return a process exit code."""
    args = options_parser(argv)
    log.debug("Version: %s", __VERSION__)

    # --netrc may be a bare flag (True) or carry an explicit path.
    netrc_path = Path(args.netrc) if isinstance(args.netrc, str) else None

    session = session_init()
    downloader = None
    try:
        credentials = get_creds(session, args.username, args.password, netrc_path)
        downloader = Downloader(
            session,
            credentials,
            show_ascii=args.ascii,
            show_info=args.info,
            download_dir=args.output,
            segments=args.segments,
        )
        signal.signal(signal.SIGINT, downloader.signal_handler)
        run(args, downloader)
    except DownloadInterrupted as exc:
        log.error("%s %s", NOTIFY_ALERT, exc)
        return EXIT_INTERRUPTED
    except KeyboardInterrupt:
        log.error("\n%s Interrupted - exiting!", NOTIFY_ALERT)
        return EXIT_INTERRUPTED
    except MobileVidsError as exc:
        # Expected, user-facing failures: report them without a traceback.
        log.error("%s %s", NOTIFY_ALERT, exc)
        log.debug("Details", exc_info=True)
        return EXIT_FAILURE
    except OSError as exc:
        log.error("%s Filesystem error: %s", NOTIFY_ALERT, exc)
        log.debug("Details", exc_info=True)
        return EXIT_FAILURE
    finally:
        if downloader is not None:
            downloader.cleanup()
        session.close()

    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
