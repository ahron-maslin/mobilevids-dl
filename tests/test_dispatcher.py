from __future__ import annotations

import argparse
from unittest.mock import MagicMock

from mobilevids.define import LOGIN_URL, SEARCH_URL
from mobilevids.dispatcher import EXIT_FAILURE, EXIT_OK, main, run


class TestRun:
    def test_search_argument_calls_search(self):
        downloader = MagicMock()
        args = argparse.Namespace(search="movie", movie=None, tv=None, episode=None, season=None)
        run(args, downloader)
        downloader.search.assert_called_once_with("movie")

    def test_movie_argument_calls_get_movie_by_id(self):
        downloader = MagicMock()
        args = argparse.Namespace(search=None, movie="42", tv=None, episode=None, season=None)
        run(args, downloader)
        downloader.get_movie_by_id.assert_called_once_with("42")

    def test_tv_with_episode_calls_get_single_episode(self):
        downloader = MagicMock()
        args = argparse.Namespace(search=None, movie=None, tv="7", episode="3", season="1")
        run(args, downloader)
        downloader.get_single_episode.assert_called_once_with("7", "1", "3")

    def test_tv_without_episode_calls_get_show_by_id(self):
        downloader = MagicMock()
        args = argparse.Namespace(search=None, movie=None, tv="7", episode=None, season="1")
        run(args, downloader)
        downloader.get_show_by_id.assert_called_once_with("7", "1")

    def test_no_arguments_calls_search_with_no_query(self):
        downloader = MagicMock()
        args = argparse.Namespace(search=None, movie=None, tv=None, episode=None, season=None)
        run(args, downloader)
        downloader.search.assert_called_once_with()


class TestMain:
    def test_search_end_to_end_returns_ok(self, requests_mock, tmp_path, monkeypatch, cache_path):
        monkeypatch.setattr("mobilevids.network.AUTH_TOKEN_CACHE", cache_path)
        requests_mock.post(LOGIN_URL, json={"auth_token": "tok", "id": "1"})
        requests_mock.get(SEARCH_URL, json={"items": []})

        exit_code = main(["-u", "user", "-p", "pass", "-o", str(tmp_path), "some movie"])

        assert exit_code == EXIT_OK

    def test_authentication_failure_is_reported_without_traceback(
        self, requests_mock, tmp_path, capsys, monkeypatch, cache_path
    ):
        monkeypatch.setattr("mobilevids.network.AUTH_TOKEN_CACHE", cache_path)
        requests_mock.post(LOGIN_URL, json={"status": "-1", "message": "bad login"})

        exit_code = main(["-u", "user", "-p", "wrong", "-o", str(tmp_path), "x"])

        assert exit_code == EXIT_FAILURE
        assert "Traceback" not in capsys.readouterr().err

    def test_password_never_appears_in_debug_output(
        self, requests_mock, tmp_path, capsys, monkeypatch, cache_path
    ):
        # Regression: network.get_creds used to log the plaintext password at
        # --debug, and the README told users to paste --debug output into
        # public bug reports.
        monkeypatch.setattr("mobilevids.network.AUTH_TOKEN_CACHE", cache_path)
        requests_mock.post(LOGIN_URL, json={"auth_token": "tok", "id": "1"})
        requests_mock.get(SEARCH_URL, json={"items": []})

        main(["-d", "-u", "user", "-p", "s3cr3t-password", "-o", str(tmp_path), "x"])

        captured = capsys.readouterr()
        assert "s3cr3t-password" not in captured.out
        assert "s3cr3t-password" not in captured.err
