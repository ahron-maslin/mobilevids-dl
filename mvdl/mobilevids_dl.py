#!/usr/bin/env python3
import logging
import os
import signal
from functools import partial

from mvdl import __VERSION__
from .options import options_parser
from .define import *
from .network import session_init, login
from .mainclass import Downloader
from .utils import signal_handler


def main():
	logging.debug(f'Version: {__VERSION__}')

	global DOWNLOAD_DIRECTORY

	if not os.path.exists(DOWNLOAD_DIRECTORY):
		logging.debug(f'Creating Directory {DOWNLOAD_DIRECTORY}')
		os.mkdir(DOWNLOAD_DIRECTORY)

	signal.signal(signal.SIGINT, signal_handler)

	args = options_parser()
	session = session_init()
	auth_token, user_id = login(session)

	downloader = Downloader(session, auth_token, user_id, args.ascii, args.info)

	if args.search:
		downloader.search(args.search)
	elif args.movie:
		downloader.get_movie_by_id(args.movie)
	elif args.tv:
		if args.episode and args.season:
			downloader.get_single_episode(args.tv, args.season, args.episode, DOWNLOAD_DIRECTORY)
		else:
			downloader.get_show_by_id(args.tv)
	else:
		downloader.search()


if __name__ == '__main__':
	main()
