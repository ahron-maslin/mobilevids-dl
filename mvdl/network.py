import requests
import netrc
import json
from json import JSONDecodeError
from wget import download, detect_filename
import os

from .define import * #only import whats needed

def session_init():
    session = requests.Session()
    try:
        creds = netrc.netrc('.netrc').authenticators('mobilevids')
        username, password = creds[0], creds[2]
    except (IOError, netrc.NetrcParseError) as e:
        raise BaseException(
        
        '''
        Did not find valid netrc file: 
        create a .netrc file with the following format:
            machine mobilevids
            login YOUR_USERNAME
            password YOUR_PASSWORD
        '''
        )
    return session, username, password



def login(session) -> str:
	payload = 'data=%7B%22Name%22%3A%22' + username + '%22%2C%22Password%22%3A%22' + password + '%22%7D'
	try:
		login_info = json.loads(session.post(
			LOGIN_URL, data=payload, headers=HEADERS).text)
	except JSONDecodeError:
		raise JSONDecodeError('cannot decode JSON - bad response!')
	print('[*] Successfully logged in!')
	return login_info['auth_token'], login_info['id'], login_info


def wget_wrapper(session, video: str, folder: str):  # wrapper for the wget module
	print(f'\nDownloading {video}')
	global CUR_DIR
	CUR_DIR = DOWNLOAD_DIRECTORY + folder
	if not os.path.exists(CUR_DIR):
		os.mkdir(CUR_DIR)
	save_path = CUR_DIR + '/' + \
		os.path.basename(video).split('?', 1)[0]
	print(f'to {save_path}')
	if not os.path.isfile(save_path):
		download(video, save_path)
		print('\n')


def get_json(session, url: str) -> dict:
	"""
	Returns JSON response from URL
	"""
	response = json.loads(session.get(url).text)
	print(f'[!] Debugging mode enabled: {response}') if self.debug else None
	return response