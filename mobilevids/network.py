import requests
import netrc
import json
from json import JSONDecodeError
from wget import detect_filename
import os
import logging
from pySmartDL import SmartDL

from .define import LOGIN_PAYLOAD, LOGIN_URL, HEADERS, AUTH_TOKEN_CACHE, GET_VIDEO_URL, NETRC_FILE_PATH


def check_auth_cache(cached_auth_file):
	"""
	Check if cached auth file exists, and return its content as a string.

	Args:
		cached_auth_file: The path to the cached auth file.

	Returns:
		The content of the cached auth file as a string.
	"""
	if os.path.isfile(cached_auth_file):
		with open(cached_auth_file, "r") as auth:
			return auth.read()


def save_cached_creds(login_info: dict):
	"""
	Write the given login_info to the cached auth file.

	Args:
		login_info: A dictionary containing login information.
	"""
	with open(AUTH_TOKEN_CACHE, "w") as cache_file:
		cache_file.write(json.dumps(login_info))



def session_init():
	"""
	Initialize a new requests session.

	Returns:
		A new requests session object.
	"""
	session = requests.Session()
	logging.debug('Created Session')
	return session


def get_creds(session, username=None, password=None) -> tuple:
	"""
	Attempt to log in to the MobileVids website using either cached credentials or
	the login credentials stored in the netrc file.

	Args:
		session: A requests session object.

	Returns:
		A tuple containing the authentication token and the user ID, in that order.
	"""
	# try using the cached credentials
	if os.path.isfile(AUTH_TOKEN_CACHE):
		with open(AUTH_TOKEN_CACHE, "r") as cache_file:
			cached_creds = json.load(cache_file)

		url = GET_VIDEO_URL.format(cached_creds['id'], cached_creds['auth_token'], "1")

		creds = get_json(session, url)

		if creds['status'] != "-1":
			logging.info("[*] Using cached credentials")
			return cached_creds['auth_token'], cached_creds['id']

	if username and password:
		logging.debug(f'logging in with username: {username} and password: {password}')
		pass
	else:
		try:
			creds = netrc.netrc(NETRC_FILE_PATH).authenticators('mobilevids')
			username, password = creds[0], creds[2]
			logging.debug('Trying netrc file %s', os.path)
		except (IOError, netrc.NetrcParseError):
			raise BaseException(
			'''
			Did not find valid netrc file: 
			Create a .netrc file in the package directory with the following format:
				machine = mobilevids
				login = MOBILEVIDS_USERNAME
				password = MOBILEVIDS_PASSWORD
			'''
			)
		
	login_string = LOGIN_PAYLOAD.format(username=username, password=password)

	try:
		login_info = json.loads(session.post(
			LOGIN_URL, data=login_string, headers=HEADERS).text)
	except JSONDecodeError:
		raise JSONDecodeError('cannot decode JSON - bad response!')
	save_cached_creds(login_info)
	logging.debug(login_info)
	logging.info('[*] Successfully logged in!')
	return login_info['auth_token'], login_info['id']


def dl_wrapper(video: str, folder):  
	"""
	Wrapper function for the SmartDL module.

	Args:
		video: The URL of the video to download.
		folder: The path to the folder in which to save the downloaded video.

	Returns:
		A SmartDL object that can be used to download the video.
	"""
	if not os.path.exists(folder): # remove this? smart_DL takes care of it
		os.mkdir(folder)

	filename = detect_filename(video)
	save_path = folder + filename

	if not os.path.isfile(save_path):
		logging.debug(f'Save path {save_path}')
		logging.info(f'Downloading {filename} to {folder}')
		dl_obj = SmartDL(video, save_path, threads=(os.cpu_count()-2))
		return dl_obj
	
	return None


def get_json(session, url: str) -> dict:
	"""
	Sends a GET request to the given URL using the provided session and returns the JSON response as a dictionary.

	Args:
		session: The session to use for the request.
		url: The URL to send the request to.

	Returns:
		A dictionary containing the JSON response.
"""
	response = session.get(url)
	response_json = json.loads(response.text)
	logging.debug(response.headers)
	logging.debug(response_json)
	
	return response_json
