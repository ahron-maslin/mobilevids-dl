import argparse
import netrc
import requests
from wget import download
import logging

from .mainclass import Downloader

def options_parser(): 
	parser = argparse.ArgumentParser(
		description='Mobilevids Downloader script', prog='mobilevids-dl.py')
	parser.add_argument('search', nargs='?')
	parser.add_argument(
		'-a', '--ascii', help='show ascii art', default=False)
	parser.add_argument(
		'-d', '--debug', help='debugs the program - duh', action='store_true')
	parser.add_argument(
		'-i', '--info', help='show info about movie/show', action='store_true')
	parser.add_argument(
		'-m', '--movie', help='downloads the ID of a movie', default=False)
	parser.add_argument(
		'-s', '--show', help='downloads the ID of a show', default=False)
	args = parser.parse_args()

	if args.debug:
		logging.basicConfig(level=logging.DEBUG,
			format='%(name)s[%(funcName)s] %(message)s')
	else:
		logging.basicConfig(level=logging.INFO,	
		format='%(message)s')
	
	return args
