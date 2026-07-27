from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mobilevids.define import GET_SEASON_URL, GET_SINGLE_EPISODE_URL, GET_VIDEO_URL, SEARCH_URL
from mobilevids.downloader import Downloader, SearchResult, _season_sort_key
from mobilevids.errors import ApiError, NoVideoFoundError


@pytest.fixture
def downloader(session, credentials, tmp_path):
    return Downloader(session, credentials, download_dir=tmp_path / "downloads")


class TestGetQuality:
    def test_prefers_highest_quality_present(self, downloader):
        info = {"src_vip_hd_1080p": "url1", "src_vip_hd": "url2"}
        assert downloader.get_quality(info) == "url1"

    def test_falls_back_to_lower_quality(self, downloader):
        assert downloader.get_quality({"src_vip_hd": "url2"}) == "url2"

    def test_skips_empty_string_source(self, downloader):
        # Regression: the old check was `info[quality] != ''`, which is
        # equivalent, but a blank/whitespace value from the API should also
        # be treated as absent.
        info = {"src_vip_hd_1080p": "", "src_vip_hd": "url2"}
        assert downloader.get_quality(info) == "url2"

    def test_raises_no_video_found_error(self, downloader):
        with pytest.raises(NoVideoFoundError, match="No video found"):
            downloader.get_quality({})


class TestSeasonSortKey:
    def test_sorts_numeric_keys_numerically(self):
        # Regression: `list(dict.keys())[0]` relied on server JSON key order.
        # "12" must sort after "9", not before it lexicographically.
        keys = ["12", "11", "2", "1", "9"]
        assert sorted(keys, key=_season_sort_key) == ["1", "2", "9", "11", "12"]


class TestSearchResult:
    def test_from_payload_defaults_missing_cat_id_to_movie(self):
        result = SearchResult.from_payload({"id": "5", "title": "X"})
        assert result.is_movie

    def test_display_title_unescapes_entities(self):
        result = SearchResult.from_payload({"id": 1, "title": "Tom &amp; Jerry", "cat_id": 1})
        assert result.display_title == "Tom & Jerry"


class TestSearch:
    def test_single_result_downloads_without_prompting(
        self, downloader, requests_mock, monkeypatch, caplog
    ):
        caplog.set_level("INFO")
        requests_mock.get(
            SEARCH_URL,
            json={"items": [{"id": 123, "title": "Single Movie", "cat_id": 1}]},
        )
        called_with: list[int] = []
        monkeypatch.setattr(downloader, "get_movie_by_id", called_with.append)

        downloader.search("query")

        assert called_with == [123]
        assert "Only one result found" in caplog.text

    def test_no_results_logs_and_returns(self, downloader, requests_mock, caplog):
        caplog.set_level("INFO")
        requests_mock.get(SEARCH_URL, json={"items": []})
        downloader.search("nothing-matches")
        assert "No results found" in caplog.text

    def test_none_items_is_treated_as_empty(self, downloader, requests_mock, caplog):
        # Regression: the API can return {"items": null}; the old code did
        # `response['items'] == None` and then indexed into it right after.
        caplog.set_level("INFO")
        requests_mock.get(SEARCH_URL, json={"items": None})
        downloader.search("nothing-matches")
        assert "No results found" in caplog.text

    def test_query_is_sent_as_encoded_param(self, downloader, requests_mock):
        requests_mock.get(SEARCH_URL, json={"items": []})
        downloader.search("harry potter & 100%")
        assert requests_mock.last_request.qs["query"] == ["harry potter & 100%"]

    def test_multiple_results_downloads_by_typed_id(self, downloader, requests_mock, monkeypatch):
        requests_mock.get(
            SEARCH_URL,
            json={
                "items": [
                    {"id": 1, "title": "Movie One", "cat_id": 1},
                    {"id": 2, "title": "Show Two", "cat_id": 2},
                ]
            },
        )
        movie_calls: list[int] = []
        show_calls: list[int] = []
        monkeypatch.setattr(downloader, "get_movie_by_id", movie_calls.append)
        monkeypatch.setattr(downloader, "get_show_by_id", show_calls.append)
        monkeypatch.setattr("builtins.input", lambda _prompt: "2")

        downloader.search("query")

        assert show_calls == [2]
        assert movie_calls == []

    def test_non_numeric_id_does_not_raise(self, downloader, requests_mock, monkeypatch, caplog):
        # Regression: `int(show_id)` on a non-numeric answer used to raise
        # ValueError straight out of search().
        caplog.set_level("ERROR")
        requests_mock.get(
            SEARCH_URL,
            json={
                "items": [
                    {"id": 1, "title": "A", "cat_id": 1},
                    {"id": 2, "title": "B", "cat_id": 1},
                ]
            },
        )
        monkeypatch.setattr("builtins.input", lambda _prompt: "not-a-number")
        downloader.search("query")
        assert "not a numeric ID" in caplog.text


class TestGetMovieById:
    def test_downloads_resolved_quality(self, downloader, requests_mock, monkeypatch):
        requests_mock.get(
            GET_VIDEO_URL,
            json={"title": "A Movie", "year": "2020", "src_vip_hd": "http://x/movie.mp4"},
        )
        calls = []
        monkeypatch.setattr(
            downloader, "_download", lambda url, folder: calls.append((url, folder))
        )

        downloader.get_movie_by_id(42)

        assert calls == [("http://x/movie.mp4", downloader.download_dir)]

    def test_missing_quality_raises_no_video_found_error(self, downloader, requests_mock):
        requests_mock.get(GET_VIDEO_URL, json={"title": "A Movie", "year": "2020"})
        with pytest.raises(NoVideoFoundError):
            downloader.get_movie_by_id(42)


class TestGetShowById:
    def _season_payload(self) -> dict[str, object]:
        return {
            "show": {"title": "A Show", "id": 7},
            "season_list": {
                "1": [["1", "1", "2019"]],
                "2": [["2", "1", "2020"], ["2", "2", "2020"]],
            },
        }

    def test_downloads_every_episode_in_chosen_season(self, downloader, requests_mock, monkeypatch):
        requests_mock.get(GET_SEASON_URL, json=self._season_payload())
        calls = []
        monkeypatch.setattr(
            downloader,
            "get_single_episode",
            lambda show_id, season, episode, path: calls.append((season, episode)),
        )

        downloader.get_show_by_id(7, season_chosen="2")

        assert calls == [("2", "1"), ("2", "2")]

    def test_sanitizes_show_title_for_directory_name(self, downloader, requests_mock, monkeypatch):
        # Regression: `download_dir + title.replace(' ', '_')` used a
        # server-controlled title directly in a filesystem path, so a title
        # like "../../../../tmp/evil" escaped the download directory.
        payload = self._season_payload()
        payload["show"] = {"title": "../../../../tmp/evil", "id": 7}
        requests_mock.get(GET_SEASON_URL, json=payload)
        seen_paths: list[Path] = []
        monkeypatch.setattr(
            downloader,
            "get_single_episode",
            lambda show_id, season, episode, path: seen_paths.append(path),
        )

        downloader.get_show_by_id(7, season_chosen="1")

        for path in seen_paths:
            assert downloader.download_dir in path.parents
            assert ".." not in path.parts

    def test_unknown_season_raises_api_error(self, downloader, requests_mock):
        requests_mock.get(GET_SEASON_URL, json=self._season_payload())
        with pytest.raises(ApiError, match="99"):
            downloader.get_show_by_id(7, season_chosen="99")

    def test_one_failed_episode_does_not_abort_the_season(
        self, downloader, requests_mock, monkeypatch, caplog
    ):
        caplog.set_level("ERROR")
        requests_mock.get(GET_SEASON_URL, json=self._season_payload())

        calls: list[str] = []

        def fake_get_single_episode(show_id, season, episode, path) -> None:
            calls.append(episode)
            if episode == "1":
                raise ApiError("boom")

        monkeypatch.setattr(downloader, "get_single_episode", fake_get_single_episode)

        downloader.get_show_by_id(7, season_chosen="2")

        assert calls == ["1", "2"]
        assert "Skipping" in caplog.text


class TestGetSingleEpisode:
    def test_downloads_into_given_path(self, downloader, requests_mock, monkeypatch, tmp_path):
        requests_mock.get(GET_SINGLE_EPISODE_URL, json={"src_vip_sd": "http://x/e01.mp4"})
        calls = []
        monkeypatch.setattr(
            downloader, "_download", lambda url, folder: calls.append((url, folder))
        )

        target = tmp_path / "show" / "season-1"
        downloader.get_single_episode(7, "1", "1", target)

        assert calls == [("http://x/e01.mp4", target)]


class TestDownload:
    def test_skips_when_destination_already_exists(self, downloader, requests_mock, caplog):
        caplog.set_level("INFO")
        downloader.download_dir.mkdir(parents=True)
        (downloader.download_dir / "movie.mp4").write_bytes(b"already here")

        downloader._download("http://x/movie.mp4", downloader.download_dir)

        assert "already downloaded" in caplog.text

    def test_runs_segmented_downloader_and_tracks_created_dir(
        self, downloader, requests_mock, tmp_path
    ):
        data = b"content"
        requests_mock.head("http://x/movie.mp4", headers={"Content-Length": str(len(data))})
        requests_mock.get(
            "http://x/movie.mp4",
            content=data,
            headers={"Content-Length": str(len(data))},
        )

        downloader._download("http://x/movie.mp4", downloader.download_dir)

        assert (downloader.download_dir / "movie.mp4").read_bytes() == data
        assert downloader.download_dir in downloader._created_dirs
        assert downloader._active_download is None


class TestCleanup:
    def test_removes_directories_it_created_if_left_empty(self, downloader, tmp_path):
        created = tmp_path / "downloads" / "empty-show"
        created.mkdir(parents=True)
        downloader._created_dirs.append(created)

        downloader.cleanup()

        assert not created.exists()
        assert downloader._created_dirs == []

    def test_leaves_directories_with_content(self, downloader, tmp_path):
        created = tmp_path / "downloads" / "show-with-file"
        created.mkdir(parents=True)
        (created / "episode.mp4").write_bytes(b"data")
        downloader._created_dirs.append(created)

        downloader.cleanup()

        assert created.exists()


class TestSignalHandler:
    def test_first_interrupt_stops_active_download_without_exiting(self, downloader):
        active = MagicMock()
        active.stopped = False
        downloader._active_download = active

        downloader.signal_handler(2, None)

        active.stop.assert_called_once()

    def test_second_interrupt_or_no_active_download_exits(self, downloader):
        downloader._active_download = None
        with pytest.raises(SystemExit):
            downloader.signal_handler(2, None)
