#!/usr/bin/env python3
import json
from json.decoder import JSONDecodeError
import argparse
from typing_extensions import Self
import requests
from wget import download
import os
import signal
import imagetoascii


USER_ID = '22342'
LEGACY_URL = 'https://mobilevids.org/legacy'
BASE_URL = 'https://mobilevids.org'
LOGIN_URL = BASE_URL + '/webapi/user/login.php'
SEARCH_URL = BASE_URL + '/webapi/videos/search.php?&p=1&user_id={USER_ID}&token={self.user_token}&query={search_query}'
GET_VIDEO_URL = ''
GET_SEASON_URL = ''
GET_SINGLE_EPISODE_URL = ''
COOKIES = {'PHPSESSID': '4lr9s6m1qqu5k02hj8sdag425j'}
PASSWORD = ''
DOWNLOAD_DIRECTORY = os.path.expanduser('~') + '/downloads/'
QUALITIES = ['src_vip_hd_1080p', 'src_vip_hd', 'src_vip_sd', 'src_free_sd']

HEADERS = {'POST': '/webapi/user/login.php HTTP/1.1',
           'Host': 'mobilevids.org',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
           'Accept': '*/*',
           'Accept-Language': 'en-US,en;q=0.5',
           'Accept-Encoding': 'gzip, deflate, br',
           'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
           'X-Requested-With': 'XMLHttpRequest',
           'Content-Length': '77',
           'Origin': 'https://mobilevids.org',
           'Connection': 'keep-alive',
           'Referer': 'https://mobilevids.org/legacy/',
           # may need to update PHPSESSID every now and then
           'Cookie': 'PHPSESSID=4lr9s6m1qqu5k02hj8sdag425j',
           'Sec-Fetch-Dest': 'empty',
           'Sec-Fetch-Mode': 'cors',
           'Sec-Fetch-Site': 'same-origin'}


def signal_handler(sig, frame):  # keyboard interrupt handler
    for file in os.listdir(DOWNLOAD_DIRECTORY):
        if file.endswith(".tmp"):
            os.remove(os.path.join(DOWNLOAD_DIRECTORY, file))
    print('\n[!] CTRL-C pressed - exiting!')
    exit(0)


signal.signal(signal.SIGINT, signal_handler)


class Downloader(object):
    def __init__(self, debug=False, ascii=False) -> None:
        super().__init__()
        self.debug = debug
        self.ascii = ascii
        self.user_token = self.login()

    def login(self) -> str:  # login function
        payload = 'data=%7B%22Name%22%3A%22Dumpbot%22%2C%22Password%22%3A%22' + PASSWORD + '%22%7D'
        try:
            login_info = json.loads(requests.post(
                LOGIN_URL, data=payload, headers=HEADERS, cookies=COOKIES).text)
            print(login_info) if self.debug else None
        except JSONDecodeError:
            raise JSONDecodeError('cannot decode JSON - bad response!')
        print('[*] Successfully logged in!')
        return login_info['auth_token']

    def wget_wrapper(self, video: str, folder: str):  # wrapper for the wget module
        print(f'\nDownloading {video}')
        if not os.path.exists(DOWNLOAD_DIRECTORY + folder):
            os.mkdir(DOWNLOAD_DIRECTORY + folder)
        save_path = DOWNLOAD_DIRECTORY + folder + '/' + \
            os.path.basename(video).split('?', 1)[0]
        print(f'to {save_path}')
        if not os.path.isfile(save_path):
            download(video, save_path)
            print('\n')

    def quality(self, info: list, debug=False):  # quality sorter

        for quality in QUALITIES:
            if quality in info and info[quality] != '':
                return info[quality]
        return 'No URL found'

    def get_json(self, url_params: str, debug=False) -> dict:
        """
        Returns JSON response from URL

        """
        response = json.loads(requests.get(BASE_URL + url_params).text)
        if debug:
            print(f'[!] Debugging mode enabled: {response}')
        return response

    def search(self):
        """
        Search for media
        """
        search_query = input('Search for something: ').lower()
        response = self.get_json(SEARCH_URL.format(USER_ID, self.user_token, search_query), self.debug)

        if response['items'] == None:
            raise ValueError(
                f'No results found for "{search_query}" - exiting!')

        print("Search results: ")
        index = 1
        for i in response['items']:
            print(
                f'{str(index)}) Name: {i["title"]}  ID: {str(i["id"])}  Type: {"Movie" if i["cat_id"] == 1 else "TV"}')

            if self.ascii:
                imagetoascii.convert_to_ascii(i['poster_thumbnail'])

            index = index + 1
        show_id = input('Enter ID: ').lower()
        for i in response['items']:
            if i['id'] == int(show_id) and i['cat_id'] > 1:
                self.get_show_by_id(show_id)
            elif i['id'] == int(show_id) and i['cat_id'] == 1:
                self.get_movie_by_id(show_id)

    def get_movie_by_id(self, movie_id: str):
        """
        Takes a movie id and downloads it to the specified directory
        """  
        movie_json = self.get_json(
            f'/webapi/videos/get_video.php?id={movie_id}&user_id={USER_ID}&token={self.user_token}', self.debug)
        print(f'[*] Downloading {movie_json["title"]} ({movie_json["year"]})')
        save_path = DOWNLOAD_DIRECTORY + \
            os.path.basename(self.quality(
                movie_json, self.debug)).split('?', 1)[0]
        if not os.path.isfile(save_path):
            download(self.quality(movie_json, self.debug), save_path)
            print('\n')

    def get_show_by_id(self, show_id: str):
        """
        Takes a show id and downloads the chosen season to the specified directory
        """
        index = 0
        season_json = self.get_json(
            f'/webapi/videos/get_season.php?show_id={show_id}&user_id={USER_ID}&token={self.user_token}', self.debug)
        print(f'[*] Showing info for {season_json["show"]["title"]}')
        tv_folder_name = season_json['show']['title'].replace(' ', '_')
        season_chosen = input(
            f'Which season (out of {list(season_json["season_list"].keys())[0]}) would you like to download? ')
    
        while index < len(season_json['season_list'][str(season_chosen)]):
            episode_info = self.get_json(
                f'/webapi/videos/get_single_episode.php?user_id={USER_ID}&token={self.user_token}&show_id={show_id}&season={season_chosen}&episode={str(season_json["season_list"][str(season_chosen)][index][1])}', self.debug)
            self.wget_wrapper(self.quality(episode_info, self.debug), tv_folder_name)
            index = index + 1

       

def options_parser():
    parser = argparse.ArgumentParser(
        description='Mobilevids Downloader script', prog='mobilevids-dl.py')
    parser.add_argument(
        '-a', '--ascii', help='show ascii art', action='store_true')
    parser.add_argument(
        '-d', '--debug', help='debugs the program- duh', action='store_true')
    parser.add_argument(
        '-i', '--info', help='show info about movie/show', action='store_true')
    parser.add_argument(
        '-m', '--movie', help='downloads the ID of a movie', default=False)
    parser.add_argument(
        '-s', '--show', help='downloads the ID of a show', default=False)
    args = parser.parse_args()

    downloader = Downloader(args.debug, args.ascii)

    if args.movie:
        downloader.get_movie_by_id(args.movie)
    elif args.show:
        downloader.get_show_by_id(args.show)
    else:
        print('[+] Movie/Show not specified - running search')
        downloader.search()


if __name__ == '__main__':  # main function
    with open('password', 'r') as p:
        PASSWORD = p.read()

    if not os.path.exists(DOWNLOAD_DIRECTORY):
        os.mkdir(DOWNLOAD_DIRECTORY)
    options_parser()
