#!/usr/bin/env python3
import json
from json.decoder import JSONDecodeError
import argparse
import netrc
import requests
from wget import download
import os
import signal

from .imagetoascii import image_to_ascii
from .define import *
from .options import options_parser
from .network import login


def signal_handler(sig, frame):  # keyboard interrupt handler
    for file in os.listdir(CUR_DIR):
        if file.endswith(".tmp"):
            filepath = os.path.join(CUR_DIR, file)
            os.remove(filepath)
    print('\n[!] CTRL-C pressed - exiting!')
    exit(0)


signal.signal(signal.SIGINT, signal_handler)






if __name__ == '__main__':  # main function      
    if not os.path.exists(CUR_DIR):
        os.mkdir(CUR_DIR)
    options_parser()
