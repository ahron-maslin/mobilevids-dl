"""Search, metadata and download orchestration."""

from __future__ import annotations

import html
import logging
import signal
import sys
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Any

import requests

from .define import (
    DEFAULT_SEGMENTS,
    DOWNLOAD_DIRECTORY,
    GET_SEASON_URL,
    GET_SINGLE_EPISODE_URL,
    GET_VIDEO_URL,
    NOTIFY_ALERT,
    NOTIFY_INFO,
    NOTIFY_QUESTION,
    NOTIFY_SUCCESS,
    QUALITIES,
    SEARCH_URL,
)
from .download import (
    DownloadInterrupted,
    SegmentedDownloader,
    filename_from_url,
    sanitize_component,
)
from .errors import ApiError, DownloadError, NoVideoFoundError
from .imagetoascii import image_to_ascii
from .network import Credentials, get_json

log = logging.getLogger(__name__)

#: ``cat_id`` value the API uses for movies; anything higher is a TV show.
MOVIE_CATEGORY_ID = 1


@dataclass(frozen=True, slots=True)
class SearchResult:
    """One entry from a search response."""

    id: int
    title: str
    cat_id: int
    poster_thumbnail: str = ""

    @property
    def is_movie(self) -> bool:
        return self.cat_id == MOVIE_CATEGORY_ID

    @property
    def display_title(self) -> str:
        """The title with HTML entities decoded, as the API escapes them."""
        return html.unescape(self.title)

    @classmethod
    def from_payload(cls, item: dict[str, Any]) -> SearchResult:
        return cls(
            id=int(item["id"]),
            title=str(item.get("title", "")),
            cat_id=int(item.get("cat_id", MOVIE_CATEGORY_ID)),
            poster_thumbnail=str(item.get("poster_thumbnail", "")),
        )


class Downloader:
    """Drive the API and hand video URLs to :class:`SegmentedDownloader`."""

    def __init__(
        self,
        session: requests.Session,
        credentials: Credentials,
        show_ascii: bool = False,
        show_info: bool = False,
        download_dir: Path = DOWNLOAD_DIRECTORY,
        segments: int | None = None,
    ) -> None:
        self.session = session
        self.credentials = credentials
        self.show_ascii = show_ascii
        self.show_info = show_info
        self.download_dir = download_dir
        self.segments = segments
        self._active_download: SegmentedDownloader | None = None
        self._created_dirs: list[Path] = []

    @property
    def _auth_params(self) -> dict[str, str]:
        return {"user_id": self.credentials.user_id, "token": self.credentials.auth_token}

    def get_quality(self, info: dict[str, Any]) -> str:
        """Return the URL of the highest available quality in ``info``."""
        for quality in QUALITIES:
            source = info.get(quality.value)
            if source:
                log.debug("Selected quality %s", quality.name)
                return str(source)
        raise NoVideoFoundError("No video found for the given URL")

    def search(self, search_query: str = "") -> None:
        """Search for a title and download the one the user picks."""
        if not search_query:
            search_query = input(f"{NOTIFY_QUESTION} Search for something: ").strip()
        if not search_query:
            log.error("%s Empty search query - nothing to do!", NOTIFY_ALERT)
            return

        response = get_json(
            self.session, SEARCH_URL, {**self._auth_params, "p": 1, "query": search_query}
        )
        items = response.get("items") or []
        results = [SearchResult.from_payload(item) for item in items]

        if not results:
            log.error('%s No results found for "%s" - exiting!', NOTIFY_ALERT, search_query)
            return

        if len(results) == 1:
            log.info("%s Only one result found - downloading it!", NOTIFY_ALERT)
            self._download_result(results[0])
            return

        log.info("Search results: ")
        for counter, result in enumerate(results, start=1):
            log.info(
                "%d) ID: %d Name: %s %s",
                counter,
                result.id,
                result.display_title,
                "(Movie)" if result.is_movie else "(TV)",
            )
            if self.show_ascii and result.poster_thumbnail:
                image_to_ascii(result.poster_thumbnail)

        chosen = self._prompt_for_result(results)
        if chosen is not None:
            self._download_result(chosen)

    def _prompt_for_result(self, results: list[SearchResult]) -> SearchResult | None:
        """Ask which result to download, accepting an ID or a list position."""
        by_id = {result.id: result for result in results}
        answer = input("Enter ID: ").strip()
        if not answer.isdigit():
            log.error("%s '%s' is not a numeric ID - exiting!", NOTIFY_ALERT, answer)
            return None

        number = int(answer)
        if number in by_id:
            return by_id[number]
        if 1 <= number <= len(results):
            # Users naturally type the list position, so accept that too.
            return results[number - 1]

        log.error("%s No result with ID %d - exiting!", NOTIFY_ALERT, number)
        return None

    def _download_result(self, result: SearchResult) -> None:
        if result.is_movie:
            self.get_movie_by_id(result.id)
        else:
            self.get_show_by_id(result.id)

    def get_movie_by_id(self, movie_id: str | int) -> None:
        """Download the movie with the given ID."""
        movie = get_json(self.session, GET_VIDEO_URL, {**self._auth_params, "id": movie_id})
        title = html.unescape(str(movie.get("title", movie_id)))
        year = movie.get("year", "unknown year")

        if self.show_info:
            self._log_metadata(movie)

        log.info("%s Downloading %s (%s)", NOTIFY_INFO, title, year)
        self._download(self.get_quality(movie), self.download_dir)

    def get_show_by_id(self, show_id: str | int, season_chosen: str | int | None = None) -> None:
        """Download one season of a TV show, prompting for it when not supplied."""
        payload = get_json(self.session, GET_SEASON_URL, {**self._auth_params, "show_id": show_id})
        show = payload.get("show") or {}
        season_list = payload.get("season_list") or {}
        if not season_list:
            raise ApiError(f"No seasons listed for show {show_id}")

        title = html.unescape(str(show.get("title", show_id)))
        log.info("%s Showing info for %s (id: %s)", NOTIFY_INFO, title, show.get("id", show_id))
        if self.show_info:
            self._log_metadata(show)

        # Keys arrive as strings in arbitrary order, so compare numerically.
        seasons = sorted(season_list, key=_season_sort_key)
        if season_chosen is None:
            season_chosen = input(
                f"{NOTIFY_QUESTION} Which season (out of {seasons[-1]}) "
                "would you like to download? "
            ).strip()

        season = str(season_chosen).strip()
        if season not in season_list:
            raise ApiError(
                f"Season {season!r} is not available for {title}. "
                f"Available seasons: {', '.join(seasons)}"
            )

        # The show title comes from the API, so it is sanitized before use as a
        # directory name; otherwise a crafted title could escape download_dir.
        season_dir = self.download_dir / sanitize_component(title, fallback=f"show_{show_id}")
        episodes = season_list[season]
        log.info(
            "%s Downloading %d episode(s) of %s season %s",
            NOTIFY_INFO,
            len(episodes),
            title,
            season,
        )

        failures = 0
        for entry in episodes:
            episode = str(entry[1])
            try:
                self.get_single_episode(show_id, season, episode, season_dir)
            except DownloadInterrupted:
                raise
            except (ApiError, DownloadError, NoVideoFoundError) as exc:
                # One missing episode should not abandon the rest of the season.
                failures += 1
                log.error("%s Skipping S%sE%s: %s", NOTIFY_ALERT, season, episode, exc)

        if failures:
            log.warning("%s Finished with %d episode(s) skipped", NOTIFY_ALERT, failures)
        else:
            log.info("%s Finished %s season %s", NOTIFY_SUCCESS, title, season)

    def get_single_episode(
        self,
        show_id: str | int,
        season: str | int,
        episode: str | int,
        path: Path | None = None,
    ) -> None:
        """Download a single episode of a show."""
        info = get_json(
            self.session,
            GET_SINGLE_EPISODE_URL,
            {**self._auth_params, "show_id": show_id, "season": season, "episode": episode},
        )
        self._download(self.get_quality(info), path or self.download_dir)

    def _download(self, video_url: str, folder: Path) -> None:
        """Download ``video_url`` into ``folder``, skipping files already present."""
        destination = folder / filename_from_url(video_url)
        if destination.exists():
            log.info("%s %s already downloaded - skipping", NOTIFY_INFO, destination.name)
            return

        if not folder.exists():
            self._created_dirs.append(folder)
        log.info("Downloading %s to %s", destination.name, folder)

        segments = self.segments if self.segments is not None else DEFAULT_SEGMENTS
        downloader = SegmentedDownloader(self.session, video_url, destination, segments=segments)
        self._active_download = downloader
        try:
            downloader.run()
        finally:
            self._active_download = None
        log.info("%s Saved %s", NOTIFY_SUCCESS, destination)

    def _log_metadata(self, info: dict[str, Any]) -> None:
        log.info(
            "Name: %s\nID: %s\nYear: %s\nDescription: %s",
            html.unescape(str(info.get("title", "unknown"))),
            info.get("id", "unknown"),
            info.get("year", "unknown"),
            html.unescape(str(info.get("plot", "none"))),
        )

    def signal_handler(self, sig: int, frame: FrameType | None) -> None:
        """Abort the running download on SIGINT and clean up partial files.

        The first interrupt asks the transfer to stop so its ``.part`` file can be
        removed as the stack unwinds; a second one exits immediately.
        """
        log.debug("SIGINT captured")
        active = self._active_download
        if active is not None and not active.stopped:
            active.stop()
            log.error("\n%s CTRL-C pressed - stopping download!", NOTIFY_ALERT)
            return

        log.error("\n%s CTRL-C pressed - exiting!", NOTIFY_ALERT)
        sys.exit(128 + signal.SIGINT)

    def cleanup(self) -> None:
        """Remove directories this run created but left empty."""
        for directory in reversed(self._created_dirs):
            try:
                if directory.is_dir() and not any(directory.iterdir()):
                    log.debug("Removing empty directory %s", directory)
                    directory.rmdir()
            except OSError as exc:  # pragma: no cover - defensive
                log.debug("Could not remove %s: %s", directory, exc)
        self._created_dirs.clear()


def _season_sort_key(season: str) -> tuple[int, str]:
    """Sort numeric season keys numerically, keeping odd keys last."""
    return (int(season), "") if season.isdigit() else (1 << 31, season)
