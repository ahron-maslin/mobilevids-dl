import requests
import netrc
import json
from json import JSONDecodeError
from wget import detect_filename
import os
import logging
from pySmartDL import SmartDL

from .define import LOGIN_PAYLOAD, LOGIN_URL, HEADERS, AUTH_TOKEN_CACHE, GET_VIDEO_URL


def check_auth_cache(cached_auth_file):
	if os.path.isfile(cached_auth_file):
		with open(cached_auth_file, "r") as auth:
			return auth.read()


def save_cached_creds(login_info: dict):
	with open(AUTH_TOKEN_CACHE, "w") as cache_file:
		cache_file.write(json.dumps(login_info))



def session_init():
	session = requests.Session()
	logging.debug('Created Session')
	return session


def login(session) -> tuple:
	'''
	first try to read in cached id and auth_token
	if it exists, check the credentials by sending a HEAD request
	'''
	if os.path.isfile(AUTH_TOKEN_CACHE):
		with open(AUTH_TOKEN_CACHE, "r") as cache_file:
			cached_creds = json.load(cache_file)

		url = GET_VIDEO_URL.format(cached_creds['id'], cached_creds['auth_token'], "1")

		creds = get_json(session, url)

		if creds['status'] != "-1":
			logging.info("[*] Using cached credentials")
			return cached_creds['auth_token'], cached_creds['id']


	try:
		creds = netrc.netrc('.netrc').authenticators('mobilevids')
		logging.debug('Trying netrc file %s', os.path)
		login_string = LOGIN_PAYLOAD.format(username=creds[0], password=creds[2])
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
	try:
		login_info = json.loads(session.post(
			LOGIN_URL, data=login_string, headers=HEADERS).text)
	except JSONDecodeError:
		raise JSONDecodeError('cannot decode JSON - bad response!')
	save_cached_creds(login_info)
	logging.debug(login_info)
	logging.info('[*] Successfully logged in!')
	return login_info['auth_token'], login_info['id']


def dl_wrapper(video: str, folder):  # wrapper for the wget module
	if not os.path.exists(folder): # remove this? smart_DL takes care of it
		os.mkdir(folder)

	filename = detect_filename(video)
	save_path = folder + filename

	if not os.path.isfile(save_path):
		logging.debug(f'Save path {save_path}')
		logging.info(f'Downloading {filename} to {folder}')
		dl_obj = SmartDL(video, save_path, threads=(os.cpu_count()-1))
		return dl_obj
	
	return None


def get_json(session, url: str) -> dict:
	"""
	Returns JSON response from URL
	"""
	response = session.get(url)
	response_json = json.loads(response.text)
	logging.debug(response.headers)
	logging.debug(response_json)
	
	return response_json
