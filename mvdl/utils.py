import os
import logging

from .define import DOWNLOAD_DIRECTORY
	

def signal_handler(sig, frame):  # keyboard interrupt handler
	global DOWNLOAD_DIRECTORY
	print(DOWNLOAD_DIRECTORY)
	for file in os.listdir(DOWNLOAD_DIRECTORY):
		if file.endswith(".tmp"):
			filepath = os.path.join(DOWNLOAD_DIRECTORY, file)
			os.remove(filepath)
	logging.error('\n[!] CTRL-C pressed - exiting!')
	exit(1)