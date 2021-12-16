#!/usr/bin/env python3
import json
from json.decoder import JSONDecodeError
import argparse
import requests
from wget import download
import os
import signal
import imagetoascii


USER_ID = '22342'
LEGACY_URL = "https://mobilevids.org/legacy"
BASE_URL = 'https://mobilevids.org'
COOKIES = {'PHPSESSID': '4lr9s6m1qqu5k02hj8sdag425j'}
PASSWORD = ''
DOWNLOAD_DIRECTORY = os.path.expanduser('~') + '/downloads/'

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
        self._index = 1
        self.query = ''
        self.response = {}
        self.tv_folder_name = ''

    def login(self) -> str:  # login function
        payload = 'data=%7B%22Name%22%3A%22Dumpbot%22%2C%22Password%22%3A%22' + PASSWORD + '%22%7D'
        try:
            login_info = requests.post(
                BASE_URL + "/webapi/user/login.php", data=payload, headers=HEADERS, cookies=COOKIES)
            login_info_res = json.loads(login_info.text)
        except JSONDecodeError:
            raise JSONDecodeError('cannot decode JSON - bad response!')
        print('[*] Successfully logged in!')
        return login_info_res['auth_token']

    def wget_wrapper(self, video: str, folder: str):  # wrapper for the wget module
        print('\nDownloading {}'.format(video))
        if not os.path.exists(DOWNLOAD_DIRECTORY + folder):
            os.mkdir(DOWNLOAD_DIRECTORY + folder)
        path = DOWNLOAD_DIRECTORY + folder + '/' + \
            os.path.basename(video).split('?', 1)[0]
        print('to {}'.format(path))
        if not os.path.isfile(path):
            download(video, path)
            print('\n')

    def quality(self, info: list, debug=False):  # quality sorter
        if 'src_vip_hd_1080p' in info and info['src_vip_hd_1080p'] != '':
            return info['src_vip_hd_1080p']
        elif 'src_vip_hd' in info and info['src_vip_hd'] != '':
            return info['src_vip_hd']
        elif 'src_vip_sd' in info and info['src_vip_sd'] != '':
            return info['src_vip_sd']
        elif 'src_free_sd' in info and info['src_free_sd'] != '':
            return info['src_free_sd']
        return 'No url found'

    # wrapper function - takes url and returns response
    def _get(self, url_params: str, debug=False) -> dict:
        response = json.loads(requests.get(BASE_URL + url_params).text)
        if debug:
            print("[!] Debugging mode enabled: {}".format(response))
        return response

    def search(self):  # search function
        self.query = input('Search for something: ').lower()
        self.response = self._get('/webapi/videos/search.php?&p=1&user_id={}&token={}&query={}'.format(
            USER_ID, self.user_token, self.query), self.debug)

        if self.response['items'] == None:
            raise ValueError(
                "No results found for '{}' - exiting!".format(self.query))

        print("Search results: ")
        for i in self.response['items']:
            print('{}) Name: {}  ID: {}  Type: {}'.format(str(self._index),
                  i['title'], str(i['id']), 'Movie' if i['cat_id'] == 1 else 'TV'))

            if self.ascii:
                imagetoascii.convert_to_ascii(i['poster_thumbnail'])

            self._index = self._index + 1
        show_id = input('Enter ID: ').lower()
        for i in self.response['items']:
            if i['id'] == int(show_id) and i['cat_id'] > 1:
                self.get_show_by_id(show_id)
            elif i['id'] == int(show_id) and i['cat_id'] == 1:
                self.get_movie_by_id(show_id)

    def get_movie_by_id(self, ID: str):  # get movie by id
        info = self._get("/webapi/videos/get_video.php?id={}&user_id={}&token={}".format(
            ID, USER_ID, self.user_token), self.debug)
        print("[*] Downloading {} ({})".format(info['title'], info['year']))
        path = DOWNLOAD_DIRECTORY + \
            os.path.basename(self.quality(info, self.debug)).split('?', 1)[0]
        if not os.path.isfile(path):
            download(self.quality(info, self.debug), path)
            print('\n')

    def get_show_by_id(self, ID: str):  # get show by id
        i = 0
        season_info = self._get(
            '/webapi/videos/get_season.php?show_id={}&user_id={}&token={}'.format(ID, USER_ID, self.user_token), self.debug)
        print('[*] Showing info for {}'.format(season_info['show']['title']))
        self.tv_folder_name = season_info['show']['title']
        which_season = input("Which season would you like to download? (out of {}) ".format(
            list(season_info['season_list'].keys())[0]))
        while i < len(season_info['season_list'][str(which_season)]):
            info = self._get("/webapi/videos/get_single_episode.php?user_id={}&token={}&show_id={}&season={}&episode={}"
                             .format(USER_ID, self.user_token, ID, which_season, str(season_info['season_list'][str(which_season)][i][1])), self.debug)
            self.wget_wrapper(self.quality(info, self.debug),
                              self.tv_folder_name.replace(' ', '_'))
            i = i + 1


def options_parser():  # argument parser
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
