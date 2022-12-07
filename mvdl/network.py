import requests
import netrc
import json
from json import JSONDecodeError
from wget import download, detect_filename
import os
import logging

from .define import * #only import whats needed


def session_init():
	session = requests.Session()
	logging.debug('Created Session')
	return session


def login(session) -> str:
	try:

		creds = netrc.netrc('.netrc').authenticators('mobilevids')
		logging.debug('Trying netrc file %s', path)
		login_string = LOGIN_PAYLOAD.format(username=creds[0], password=creds[2])
	except (IOError, netrc.NetrcParseError) as e:
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
	logging.debug(login_info)
	logging.info('[*] Successfully logged in!')
	return login_info['auth_token'], login_info['id']


def wget_wrapper(video: str, folder):  # wrapper for the wget module
	print(folder)
	if not os.path.exists(folder):
		os.mkdir(folder)
	print(detect_filename(video))
	save_path = folder + detect_filename(video)
	logging.debug(save_path)
	logging.info(f'Downloading {video} to {save_path}')
	if not os.path.isfile(save_path):
		download(video, save_path)


def get_json(session, url: str) -> dict:
	"""
	Returns JSON response from URL
	"""
	response = json.loads(session.get(url).text)
	logging.debug(response)
	return response