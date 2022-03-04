#!/usr/bin/env python3
import json
from json.decoder import JSONDecodeError
import argparse
import netrc
import requests
from wget import download
import os
import signal
import imagetoascii


LEGACY_URL = 'https://mobilevids.org/legacy'
BASE_URL = 'https://mobilevids.org'
LOGIN_URL = 'https://mobilevids.org/webapi/user/login.php'
SEARCH_URL = 'https://mobilevids.org/webapi/videos/search.php?&p=1&user_id={}&token={}&query={}'
GET_VIDEO_URL = 'https://mobilevids.org/webapi/videos/get_video.php?user_id={}&token={}&id={}'
GET_SEASON_URL = 'https://mobilevids.org/webapi/videos/get_season.php?user_id={}&token={}&show_id={}'
GET_SINGLE_EPISODE_URL = 'https://mobilevids.org/webapi/videos/get_single_episode.php?user_id={}&token={}&show_id={}&season={}&episode={}'
# Can fill these in manually
PASSWORD = '' 
USERNAME = ''
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
           'Sec-Fetch-Dest': 'empty',
           'Sec-Fetch-Mode': 'cors',
           'Sec-Fetch-Site': 'same-origin'
           }


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
        self.user_token, self.user_id = self.login()

    def login(self) -> str:  # login function
        payload = 'data=%7B%22Name%22%3A%22' + USERNAME + '%22%2C%22Password%22%3A%22' + PASSWORD + '%22%7D'
        try:
            login_info = json.loads(session.post(
                LOGIN_URL, data=payload, headers=HEADERS).text)
            print(login_info) if self.debug else None
        except JSONDecodeError:
            raise JSONDecodeError('cannot decode JSON - bad response!')
        print('[*] Successfully logged in!')
        return login_info['auth_token'], login_info['id']

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

    def get_quality(self, info: list): 
        """
        
        """
        for quality in QUALITIES:
            if quality in info and info[quality] != '':
                return info[quality]
        return 'No URL found'

    def get_json(self, url: str) -> dict:
        """
        Returns JSON response from URL

        """
        response = json.loads(session.get(url).text)
        print(f'[!] Debugging mode enabled: {response}') if self.debug else None
        return response

    def search(self):
        """
        Search for media
        """
        search_query = input('Search for something: ').lower()
        response = self.get_json(SEARCH_URL.format(self.user_id, self.user_token, search_query))

        if response['items'] == None:
            raise ValueError(
                f'No results found for "{search_query}" - exiting!')

        print("Search results: ")
        counter = 1
        for i in response['items']:
            print(
                f'{str(counter)}) Name: {i["title"]}  ID: {str(i["id"])}  Type: {"Movie" if i["cat_id"] == 1 else "TV"}')
            if self.ascii:
                imagetoascii.convert_to_ascii(i['poster_thumbnail'])
            counter = counter + 1

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
        movie_json = self.get_json(GET_VIDEO_URL.format(self.user_id, self.user_token, movie_id))
        print(f'[*] Downloading {movie_json["title"]} ({movie_json["year"]})')
        save_path = DOWNLOAD_DIRECTORY + \
            os.path.basename(self.get_quality(
                movie_json)).split('?', 1)[0]
        if not os.path.isfile(save_path):
            download(self.get_quality(movie_json), save_path)
            print('\n')

    def get_show_by_id(self, show_id: str):
        """
        Takes a show id and downloads the chosen season to the specified directory
        """
        index = 0
        season_json = self.get_json(GET_SEASON_URL.format(self.user_id, self.user_token, show_id))
        print(f'[*] Showing info for {season_json["show"]["title"]}')
        tv_folder_name = season_json['show']['title'].replace(' ', '_')
        season_chosen = input(
            f'Which season (out of {list(season_json["season_list"].keys())[0]}) would you like to download? ')
    
        while index < len(season_json['season_list'][str(season_chosen)]):
            episode = str(season_json["season_list"][str(season_chosen)][index][1])
            episode_info = self.get_json(GET_SINGLE_EPISODE_URL.format(self.user_id, self.user_token, show_id, season_chosen, episode))
            self.wget_wrapper(self.get_quality(episode_info), tv_folder_name)
            index = index + 1

       

def options_parser():
    parser = argparse.ArgumentParser(
        description='Mobilevids Downloader script', prog='mobilevids-dl.py')
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

    downloader = Downloader(args.debug, args.ascii)

    if args.movie:
        downloader.get_movie_by_id(args.movie)
    elif args.show:
        downloader.get_show_by_id(args.show)
    else:
        print('[+] Movie/Show not specified - running search')
        downloader.search()


if __name__ == '__main__':  # main function
    session = requests.Session()
    try:
        creds = netrc.netrc('.netrc').authenticators('mobilevids')
        USERNAME, PASSWORD = creds[0], creds[2]
    except (IOError, netrc.NetrcParseError) as e:
        raise BaseException(
        'Did not find valid netrc file:\n' 
        'create a .netrc file with the following format:\n'
        '   machine mobilevids\n'
        '   login YOUR_USERNAME\n'
        '   password YOUR_PASSWORD\n')

           
    if not os.path.exists(DOWNLOAD_DIRECTORY):
        os.mkdir(DOWNLOAD_DIRECTORY)
    options_parser()
