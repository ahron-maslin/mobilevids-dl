import argparse
import logging


def options_parser(): 
	# groups for general options and media options
	parser = argparse.ArgumentParser(
		description='Mobilevids Downloader script', prog='mobilevids_dl')

	parser.add_argument('search', nargs='?')
	parser.add_argument(
		'-a', 
		'--ascii', 
		help='show ascii art', 
		action='store_true')

	parser.add_argument(
		'-d', 
		'--debug', 
		help='debugs the program - duh', 
		action='store_true')

	parser.add_argument(
		'-i', 
		'--info', 
		help='show info about movie/show', 
		action='store_true')
	
	parser.add_argument(
		'-e', 
		'--episode', 
		help='download a single episode (must be used with -t [TV ID] and -s [SEASON]', 
		default=False)

	parser.add_argument(
		'-m', 
		'--movie', 
		help='downloads the ID of a movie', 
		default=False)
	
	parser.add_argument(
		'-n',
		'--netrc',
		help='use netrc for reading passwords, uses default'
        ' location if no path specified',
		default=False
	)
	
	parser.add_argument(
		'-p',
		'--password',
		help='provide a mobilevids password',
		default=False
	)

	parser.add_argument(
		'-s', 
		'--season', 
		help='specify season to download (must use with -t)', 
		default=False)

	parser.add_argument(
		'-t', 
		'--tv', 
		help='download a TV show based on it\'s ID', 
		default=False)
	
	parser.add_argument(
		'-u',
		'--username',
		help='provide a Mobilevids username',
		default=False
	)

	args = parser.parse_args()

	if args.debug:
		logging.basicConfig(level=logging.DEBUG,
			force=True,
			format='%(name)s[%(funcName)s] %(message)s')
	else:
		logging.basicConfig(level=logging.INFO,	
		force=True,
		format='%(message)s')
	
	logging.debug(f'Program arguments {args}')
	return args
