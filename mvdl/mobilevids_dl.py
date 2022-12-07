#!/usr/bin/env python3
import json
from json.decoder import JSONDecodeError
import argparse
import netrc
import logging
from wget import download
import os
import signal

from mvdl import __VERSION__
from .options import options_parser
from .imagetoascii import image_to_ascii
from .define import *
from .network import session_init, login
from .mainclass import Downloader


def signal_handler(sig, frame):  # keyboard interrupt handler
	for file in os.listdir(CUR_DIR):
		if file.endswith(".tmp"):
			filepath = os.path.join(CUR_DIR, file)
			os.remove(filepath)
	print('\n[!] CTRL-C pressed - exiting!')
	exit(0)


signal.signal(signal.SIGINT, signal_handler)


def main():
	logging.debug(__VERSION__)

	if not os.path.exists(CUR_DIR):
		os.mkdir(CUR_DIR)

	args = options_parser()
	print(args)
	logging.error(args)

	session = session_init()
	auth_token, user_id = login(session)

	downloader = Downloader(auth_token, user_id, args.ascii, args.info)

	if args.search:
		downloader.search(args.search)
	elif args.movie:
		downloader.get_movie_by_id(args.movie)
	elif args.show:
		downloader.get_show_by_id(args.show)
	else:
		print('[+] Movie/Show not specified - running search')
		downloader.search()



if __name__ == '__main__':
	main()
