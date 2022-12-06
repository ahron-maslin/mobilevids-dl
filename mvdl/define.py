from os import path

LEGACY_URL = 'https://mobilevids.org/legacy'
BASE_URL = 'https://mobilevids.org'
LOGIN_URL = 'https://mobilevids.org/webapi/user/login.php'
SEARCH_URL = 'https://mobilevids.org/webapi/videos/search.php?&p=1&user_id={}&token={}&query={}'
GET_VIDEO_URL = 'https://mobilevids.org/webapi/videos/get_video.php?user_id={}&token={}&id={}'
GET_SEASON_URL = 'https://mobilevids.org/webapi/videos/get_season.php?user_id={}&token={}&show_id={}'
GET_SINGLE_EPISODE_URL = 'https://mobilevids.org/webapi/videos/get_single_episode.php?user_id={}&token={}&show_id={}&season={}&episode={}'
DOWNLOAD_DIRECTORY = path.expanduser('~') + '/downloads/'
CUR_DIR = DOWNLOAD_DIRECTORY
QUALITIES = ['src_vip_hd_1080p', 'src_vip_hd', 'src_vip_sd', 'src_free_sd']
HEADERS = {'POST': '/webapi/user/login.php HTTP/1.1',
           'Host': 'mobilevids.org',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
           'Accept': '*/*',
           'Accept-Language': 'en-US,en;q=0.5',
           'Accept-Encoding': 'gzip, deflate, br',
           'sec-ch-ua' : '".Not/A)Brand";v="99", "Google Chrome";v="103", "Chromium";v="103"',
           'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
           'Cookie': 'menuNodes=[{"name":"Movies","icon":"mdi-movie","children":[{"name":"Browse","path":"/movies","icon":"mdi-view-list"},{"name":"Popular","path":"/top_movies","icon":"mdi-movie-filter"}]},{"name":"TV Shows","icon":"mdi-remote-tv","children":[{"name":"Browse ","path":"/tvshows","icon":"mdi-view-list"},{"name":"Popular ","path":"/top_shows","icon":"mdi-monitor-star"},{"name":"Calendar","path":"/show_calendar","icon":"mdi-calendar"}]}]',
           'X-Requested-With': 'XMLHttpRequest',
           'Content-Length': '77',
           'Origin': 'https://mobilevids.org',
           'Connection': 'keep-alive',
           'Referer': 'https://mobilevids.org/legacy/',
           'Sec-Fetch-Dest': 'empty',
           'Sec-Fetch-Mode': 'cors',
           'Sec-Fetch-Site': 'same-origin',
           'sec-ch-ua-platform' : '"Windows"'
           }

