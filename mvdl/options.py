import argparse
import netrc
import requests
from wget import download

from .mainclass import Downloader

def options_parser(): 
    parser = argparse.ArgumentParser(
        description='Mobilevids Downloader script', prog='mobilevids-dl.py')
    parser.add_argument('search', nargs='?')
    parser.add_argument(
        '-a', '--ascii', help='show ascii art', action='store_true')
    parser.add_argument(
        '-d', '--debug', help='debugs the program - duh', action='store_true')
    parser.add_argument(
        '-i', '--info', help='show info about movie/show', action='store_true')
    parser.add_argument(
        '-m', '--movie', help='downloads the ID of a movie', default=False)
    parser.add_argument(
        '-s', '--show', help='downloads the ID of a show', default=False)
    args = parser.parse_args()

    downloader = Downloader(args.debug, args.ascii, args.info)

    if args.search:
        downloader.search(args.search)
    elif args.movie:
        downloader.get_movie_by_id(args.movie)
    elif args.show:
        downloader.get_show_by_id(args.show)
    else:
        print('[+] Movie/Show not specified - running search')
        downloader.search()
    