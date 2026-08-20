"""Static configuration: API endpoints, filesystem paths and console glyphs."""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path

from mobilevids import __PKGNAME__


def _user_data_dir() -> Path:
    """Return the per-user directory that holds downloads and cached credentials."""
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return base / __PKGNAME__
    return Path.home()


def normalize_path(path: str | Path) -> Path:
    """Resolve ``path`` against the per-user data directory."""
    return _user_data_dir() / path


BASE_URL = "https://mobilevids.org/"
LOGIN_URL = BASE_URL + "webapi/user/login.php"
SEARCH_URL = BASE_URL + "webapi/videos/search.php"
GET_VIDEO_URL = BASE_URL + "webapi/videos/get_video.php"
GET_SEASON_URL = BASE_URL + "webapi/videos/get_season.php"
GET_SINGLE_EPISODE_URL = BASE_URL + "webapi/videos/get_single_episode.php"

DOWNLOAD_DIRECTORY = normalize_path("downloads")
AUTH_TOKEN_CACHE = normalize_path(".mvdl_auth_token")
NETRC_FILE_PATH = normalize_path(".netrc")

#: Machine name to look up in the netrc file. Must match the documented value.
NETRC_MACHINE = "mobilevids"

#: Environment variables consulted before falling back to the netrc file.
ENV_USERNAME = "MOBILEVIDS_USERNAME"
# A variable name, not a secret.
ENV_PASSWORD = "MOBILEVIDS_PASSWORD"  # noqa: S105  # nosec B105

#: (connect, read) timeout in seconds applied to every API request.
REQUEST_TIMEOUT = (10, 30)

#: Number of parallel connections used for a single video download.
DEFAULT_SEGMENTS = 4

#: Bytes read per socket recv while streaming a download.
CHUNK_SIZE = 1 << 20


class Quality(StrEnum):
    """Video source fields, ordered best quality first."""

    HD_1080P = "src_vip_hd_1080p"
    HD = "src_vip_hd"
    SD = "src_vip_sd"
    FREE_SD = "src_free_sd"


#: Preference order used when picking a video source.
QUALITIES: tuple[Quality, ...] = tuple(Quality)

#: Minimal headers the API requires; requests derives Host and Content-Length.
HEADERS = {
    "User-Agent": f"{__PKGNAME__}/python-requests",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://mobilevids.org",
    "Referer": "https://mobilevids.org/legacy/",
}

NOTIFY_ALERT = "⚠️"
NOTIFY_INFO = "🛈"
NOTIFY_QUESTION = "❓"
NOTIFY_SUCCESS = "✅"
