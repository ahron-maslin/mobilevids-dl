import os
import logging
import html

from .define import DOWNLOAD_DIRECTORY, QUALITIES, SEARCH_URL, GET_VIDEO_URL, GET_SEASON_URL, GET_SINGLE_EPISODE_URL
from .imagetoascii import image_to_ascii
from .network import get_json, dl_wrapper


class Downloader:
	"""
    Class for downloading movies and TV shows from the streaming service.

    Attributes:
        session (requests.Session): The session object used for making HTTP requests.
        auth_token (str): Authentication token used for accessing the streaming service.
        user_id (str): User ID associated with the streaming service account.
        ascii (bool): Whether to display movie/TV show poster thumbnails in ASCII art.
        info (bool): Whether to display information about the movie/TV show.
        download_dir (str): Directory where downloaded files will be stored.
        dl_obj (dl_wrapper): Download object for handling file downloads.

    Methods:
        get_quality(info: dict) -> str:
            Returns the best quality available for the given movie or TV show.

        search(search_query: str = ''):
            Searches for a movie or TV show with the given search query and prompts the user to select one to download.

        get_movie_by_id(movie_id: str):
            Downloads the movie with the given ID.

        get_show_by_id(show_id: str, season_chosen=None):
            Downloads the TV show with the given ID and prompts the user to select a season to download.

        get_single_episode(show_id: str, season: str, episode: str, path: str):
            Downloads a single episode of the given TV show.

        signal_handler(sig, frame):
            Handles keyboard interrupts during file downloads and removes incomplete downloads.
  	"""
	def __init__(self, session, auth_token, user_id, ascii=False, info=False) -> None:
		self.session = session
		self.auth_token = auth_token
		self.user_id = user_id
		self.ascii = ascii
		self.info = info
		self.download_dir = DOWNLOAD_DIRECTORY
		self.dl_obj = None


	def get_quality(self, info): 
		"""
    Returns the best quality available for the given movie or TV show.

    Args:
        info (dict): Dictionary containing information about the movie or TV show.

    Returns:
        str: The quality (e.g. "1080p") of the video with the highest available quality.
        
    Raises:
        Exception: If no video is found for the given URL.
    	"""
		for quality in QUALITIES:
			if quality in info and info[quality] != '':
				return info[quality]
		raise Exception(
			'No video found for the given URL'
		)


	def search(self, search_query:str = ''):
		"""
    Searches for a movie or TV show with the given search query and prompts the user to select one to download.

    Args:
        search_query (str): The search query to use. If not provided, the user will be prompted to enter one.
    """
		if not search_query:
			search_query = input('[?] Search for something: ').lower()
		response = get_json(self.session, SEARCH_URL.format(self.user_id, self.auth_token, search_query))

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
			logging.info(f'{str(counter + 1)}) '
									 f'ID: {str(i["id"])} '
									 f'Name: {html.unescape(i["title"])} {"(Movie)" if i["cat_id"] == 1 else "(TV)"}'
									 )

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
    Downloads the movie with the given ID.

    Args:
        movie_id (str): The ID of the movie to download.
    """  
		movie_json = get_json(self.session, GET_VIDEO_URL.format(self.user_id, self.auth_token, movie_id))
		if self.info:
			logging.info(f"Name: {movie_json['title']}\n"
									 f"ID: {movie_json['id']}\n"
									 f"Year: {movie_json['year']}\n"
									 f"Description: {movie_json['plot']}")

		logging.info(f'[*] Downloading {movie_json["title"]} ({movie_json["year"]})')
		self.dl_obj = dl_wrapper(self.get_quality(movie_json), self.download_dir)
		if self.dl_obj:
			self.dl_obj.start()


	def get_show_by_id(self, show_id: str, season_chosen=None):
		"""
    Downloads the TV show with the given ID and prompts the user to select a season to download.

    Args:
        show_id (str): The ID of the TV show to download.
        season_chosen (str): The season to download. If not provided, the user will be prompted to select one.
    """
		season_json = get_json(self.session, GET_SEASON_URL.format(self.user_id, self.auth_token, show_id))
		season_title = season_json["show"]["title"]
		season_id = season_json['show']['id']
		logging.info(f'[*] Showing info for {season_title} (id: {season_id})')
		self.download_dir = self.download_dir + season_title.replace(' ', '_') + '/'
		if self.info:
			logging.info(f"Name: {season_json['show']['title']}\n"
										f"ID: {season_json['show']['id']}\n"
										f"Year: {season_json['show']['year']}\n"
										f"Description: {season_json['show']['plot']}\n")
		if not season_chosen:
			season_chosen = input(
				f'[?] Which season (out of {list(season_json["season_list"].keys())[0]}) would you like to download? ')

		num_episodes = len(season_json['season_list'][str(season_chosen)])

		for i in range(num_episodes):
			episode = str(season_json['season_list'][str(season_chosen)][i][1])
			self.get_single_episode(show_id, season_chosen, episode, self.download_dir)


	def get_single_episode(self, show_id: str, season: str, episode: str, path: str):
		"""
    Downloads a single episode of the given TV show.

    Args:
        show_id (str): The ID of the TV show to download.
        season (str): The season number of the episode.
        episode (str): The episode number of the episode.
        path (str): The directory where the downloaded file will be saved.
    """
		episode_info = get_json(self.session, GET_SINGLE_EPISODE_URL.format(self.user_id, self.auth_token, show_id, season, episode))
		self.dl_obj = dl_wrapper(self.get_quality(episode_info), path)
		if self.dl_obj:
			self.dl_obj.start()


	def signal_handler(self, sig, frame):
		"""
    Handles keyboard interrupts during file downloads and removes incomplete downloads.

    Args:
        sig: The signal number.
        frame: The interrupted stack frame.
    """
		logging.debug('SIGINT captured')
		if self.dl_obj:
			self.dl_obj.stop()
		for file in os.listdir(self.download_dir):
			if file.endswith(".00", -4, -1):
				'''
				  Smart_DL downloads file in chunks ending in ".00x" 
					where x is a number corresponding to the thread that is being used
				'''
				filepath = os.path.join(self.download_dir, file)
				os.remove(filepath)
		if self.download_dir and len(os.listdir(self.download_dir)) == 0 and self.download_dir is not DOWNLOAD_DIRECTORY:
			'''
			remove download dir if not the default directory
			'''
			logging.debug(f'Removing {self.download_dir}')
			os.rmdir(self.download_dir)
		logging.error('\n[!] CTRL-C pressed - exiting!')
		exit(1)
		