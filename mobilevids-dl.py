#!/usr/bin/env python3
import json
from json.decoder import JSONDecodeError
import argparse
import requests
from wget import download
import os
import signal


user_id = '22342'
legacy_url = "https://mobilevids.org/legacy"
base_url = 'https://mobilevids.org'
cookies = {'PHPSESSID':'4lr9s6m1qqu5k02hj8sdag425j'}
PASSWORD = ''

headers = {'POST':'/webapi/user/login.php HTTP/1.1',
'Host':'mobilevids.org',
'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
'Accept':'*/*',
'Accept-Language':'en-US,en;q=0.5',
'Accept-Encoding':'gzip, deflate, br',
'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
'X-Requested-With':'XMLHttpRequest',
'Content-Length':'77',
'Origin':'https://mobilevids.org',
'Connection':'keep-alive',
'Referer':'https://mobilevids.org/legacy/',
'Cookie':'PHPSESSID=4lr9s6m1qqu5k02hj8sdag425j', # may need to update PHPSESSID every now and then
'Sec-Fetch-Dest':'empty',
'Sec-Fetch-Mode':'cors',
'Sec-Fetch-Site':'same-origin'}



def signal_handler(sig, frame): # keyboard interrupt handler
    print('\n[!] CTRL-C pressed - exiting!')
    exit(0)

signal.signal(signal.SIGINT, signal_handler)

class Downloader(object): 
    def __init__(self, debug=False) -> None:
        super().__init__()
        self.debug = debug
        self.user_token = self.login()
        self._index = 1
        self.query = ''
        self.response = {}


    def login(self) -> str:  # login function
        payload = 'data=%7B%22Name%22%3A%22Dumpbot%22%2C%22Password%22%3A%22' + PASSWORD + '%22%7D'
        try:
            login_info = requests.post(base_url + "/webapi/user/login.php", data=payload, headers=headers, cookies=cookies)
            login_info_res = json.loads(login_info.text)
        except JSONDecodeError:
            raise JSONDecodeError('cannot decode JSON - bad response!')
        print('[*] Successfully logged in!')
        return login_info_res['auth_token']


    def wget_wrapper(self, video: str):  # wrapper for the wget module  
        print('\nDownloading {}'.format(video))
        path = 'downloads/' + os.path.basename(video).split('?', 1)[0]
        if not os.path.isfile(path):
            download(video, path)    
            print('\n')


    def quality(self, info: list, debug=False):
        if 'src_vip_hd_1080p' in info and info['src_vip_hd_1080p'] != '':
            return info['src_vip_hd_1080p']
        elif 'src_vip_hd' in info and info['src_vip_hd'] != '':
            return info['src_vip_hd']
        elif 'src_vip_sd' in info and info['src_vip_sd'] != '':
            return info['src_vip_sd']
        elif 'src_free_sd' in info and info['src_free_sd'] != '':
            return info['src_free_sd']
        return 'No url found'


    def _get(self, url_params: str, debug=False) -> dict:  # wrapper function - takes url and returns response
        response = json.loads(requests.get(base_url + url_params).text)
        if debug:
            print("[!] Debugging mode response: {}".format(response))
        return response
          

    def search(self):  
        self.query = input('Search for something: ').lower()
        self.response = self._get('/webapi/videos/search.php?&p=1&user_id={}&token={}&query={}'.format(user_id, self.user_token, self.query), self.debug)

        if self.response['items'] == None:
            raise ValueError("No results found for '{}' - exiting!".format(self.query))

        print("Search results: ")
        for i in self.response['items']:
            print('{}) Name: {}  ID: {}  Type: {}'.format(str(self._index), i['title'], str(i['id']), 'Movie' if i['cat_id'] == 1 else 'TV'))
            self._index = self._index + 1
        show_id = input('Enter ID: ').lower()
        for i in self.response['items']:
            if i['id'] == int(show_id) and i['cat_id'] > 1:
                self.get_show_by_id(show_id)
            elif i['id'] == int(show_id) and i['cat_id'] == 1:
                self.get_movie_by_id(show_id)


    def get_movie_by_id(self, id: str): # get movie by id
        info = self._get("/webapi/videos/get_video.php?id={}&user_id={}&token={}".format(id, user_id, self.user_token), self.debug)
        print("[*] Downloading {}".format(info['title']))
        path = 'downloads/' + os.path.basename(self.quality(info, self.debug)).split('?', 1)[0]
        if not os.path.isfile(path):
            download(self.quality(info, self.debug), path)
        


    def get_show_by_id(self, id: str):  # get show by id
        season_info = self._get('/webapi/videos/get_season.php?show_id={}&user_id={}&token={}'.format(id, user_id, self.user_token), self.debug)
        print('[*] Showing info for {}'.format(season_info['show']['title']))
        which_season = input("Which season would you like to download? (out of {}) ".format(list(season_info['season_list'].keys())[0])) 
        i = 1
        while i < len(season_info['season_list'][str(which_season)]): 
            info = self._get("/webapi/videos/get_single_episode.php?user_id={}&token={}&show_id={}&season={}&episode={}"
            .format(user_id, self.user_token, id, which_season, str(season_info['season_list'][str(which_season)][i][1])), self.debug)            
            self.wget_wrapper(self.quality(info, self.debug))
            i = i + 1

        
def options_parser():  # argument parser
    parser = argparse.ArgumentParser(description='Mobilevids Downloader script', prog='mobilevids-dl.py')
    parser.add_argument('-d', '--debug', help='debugs the program- duh', action='store_true')
    parser.add_argument('-m', '--movie', help='downloads the ID of a movie', default=False)
    parser.add_argument('-s', '--show', help='downloads the ID of a show', default=False)
    args = parser.parse_args()

    downloader = Downloader(args.debug)
   
    if args.movie:
        downloader.get_movie_by_id(args.movie)
    elif args.show:
        downloader.get_show_by_id(args.show)
    else:
        print('[!] Movie/Show not specified - running search')
        downloader.search()


if __name__ == '__main__':  # main function
    with open('password', 'r') as p:
        PASSWORD = p.read()

    if not os.path.exists('downloads'):
        os.mkdir('downloads')
    options_parser()   
