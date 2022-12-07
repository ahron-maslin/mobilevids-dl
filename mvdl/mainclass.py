import os
from wget import download
import logging

from. define import *
from .imagetoascii import image_to_ascii


class Downloader:
	def __init__(self, auth_token, user_id, ascii=False, info=False) -> None:
		self.auth_token = auth_token
		self.user_id = user_id
		self.ascii = ascii
		self.info = info


	def get_quality(self, info: list): 
		"""
		Self explanatory...
		"""
		for quality in QUALITIES:
			if quality in info and info[quality] != '':
				return info[quality]
		return 'No URL found' # raise instead?

	def search(self, search_query = None):
		"""
		Search for media
		"""
		if not search_query:
			search_query = input('[?] Search for something: ').lower()
		response = self.session.get_json(SEARCH_URL.format(self.user_id, self.user_token, search_query))

		if response['items'] == None:
				logging.error(f'[!] No results found for "{search_query}" - exiting!')
				exit()

		if len(response['items']) == 1:
			logging.info("[!] Only one result found - downloading it!")
			first_id = response['items'][0]
			self.get_movie_by_id(first_id['id']) if first_id['cat_id'] == 1 else self.get_show_by_id(first_id['id'])
			exit()

		logging.info("Search results: ")
		for counter, i in enumerate(response['items']):
			logging.info(
				f'{str(counter + 1)}) Name: {i["title"]}  ID: {str(i["id"])}  Type: {"Movie" if i["cat_id"] == 1 else "TV"}')
			if self.ascii:
				image_to_ascii(i['poster_thumbnail'])

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
		movie_json = self.session.get_json(GET_VIDEO_URL.format(self.user_id, self.user_token, movie_id))
		if self.info:
			logging.info(f"Name: {movie_json['title']}\nID: {movie_json['id']}\nYear: {movie_json['year']}\nDescription: {movie_json['plot']}")
		logging.info(f'[*] Downloading {movie_json["title"]} ({movie_json["year"]})')
		save_path = DOWNLOAD_DIRECTORY + \
			os.path.basename(self.get_quality(
				movie_json)).split('?', 1)[0]
		if not os.path.isfile(save_path):
			download(self.get_quality(movie_json), save_path)
			logging.info('\n')

	def get_show_by_id(self, show_id: str):
		"""
		Takes a show id and downloads the chosen season to the specified directory
		"""
		index = 0
		season_json = self.session.get_json(GET_SEASON_URL.format(self.user_id, self.user_token, show_id))
		logging.info(f'[*] Showing info for {season_json["show"]["title"]}')
		tv_folder_name = season_json['show']['title'].replace(' ', '_')
		if self.info:
			logging.info(f"Name: {season_json['show']['title']}\nID: {season_json['show']['id']}\nYear: {season_json['show']['year']}\nDescription: {season_json['show']['plot']}\n")
	
		season_chosen = input(
			f'[?] Which season (out of {list(season_json["season_list"].keys())[0]}) would you like to download? ')
	   
		while index < len(season_json['season_list'][str(season_chosen)]):
			episode = str(season_json['season_list'][str(season_chosen)][index][1])
			episode_info = self.session.get_json(GET_SINGLE_EPISODE_URL.format(self.user_id, self.user_token, show_id, season_chosen, episode))
			self.wget_wrapper(self.get_quality(episode_info), tv_folder_name)
			index = index + 1

	   