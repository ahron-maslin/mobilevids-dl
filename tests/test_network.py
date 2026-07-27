from __future__ import annotations

import json
import stat
from urllib.parse import unquote_plus

import pytest
import requests

from mobilevids.define import GET_VIDEO_URL, LOGIN_URL
from mobilevids.errors import ApiError, AuthenticationError
from mobilevids.network import (
    Credentials,
    get_creds,
    get_json,
    load_cached_creds,
    login,
    read_netrc_credentials,
    resolve_credentials,
    save_cached_creds,
)


class TestGetJson:
    def test_decodes_json_object(self, session, requests_mock):
        requests_mock.get(LOGIN_URL, json={"a": 1})
        assert get_json(session, LOGIN_URL) == {"a": 1}

    def test_encodes_params_instead_of_interpolating(self, session, requests_mock):
        # Regression: the old code built URLs with str.format(), so a query like
        # "harry potter & 100%" broke the request. requests must see it as a
        # single, correctly encoded query parameter.
        requests_mock.get(LOGIN_URL, json={})
        get_json(session, LOGIN_URL, {"query": "harry potter & 100% #1"})
        assert requests_mock.last_request.qs["query"] == ["harry potter & 100% #1"]

    def test_http_error_raises_api_error(self, session, requests_mock):
        requests_mock.get(LOGIN_URL, status_code=500, text="boom")
        with pytest.raises(ApiError):
            get_json(session, LOGIN_URL)

    def test_non_json_body_raises_api_error_not_typeerror(self, session, requests_mock):
        # Regression: mobilevids.network used to `raise JSONDecodeError('msg')`
        # with only one argument, which itself raised TypeError instead of
        # reporting the real problem.
        requests_mock.get(LOGIN_URL, text="<html>not json</html>")
        with pytest.raises(ApiError):
            get_json(session, LOGIN_URL)

    def test_non_object_json_raises_api_error(self, session, requests_mock):
        requests_mock.get(LOGIN_URL, json=[1, 2, 3])
        with pytest.raises(ApiError):
            get_json(session, LOGIN_URL)

    def test_network_failure_raises_api_error(self, session, requests_mock):
        requests_mock.get(LOGIN_URL, exc=requests.ConnectionError)
        with pytest.raises(ApiError):
            get_json(session, LOGIN_URL)


class TestCredentialCache:
    def test_round_trips(self, cache_path):
        save_cached_creds({"auth_token": "tok", "id": "1"}, cache_path)
        assert load_cached_creds(cache_path) == Credentials("tok", "1")

    def test_written_file_is_owner_only(self, cache_path):
        # Regression: the token cache used to be written with the default
        # umask (typically 0644), leaving a bearer token world-readable.
        save_cached_creds({"auth_token": "tok", "id": "1"}, cache_path)
        mode = stat.S_IMODE(cache_path.stat().st_mode)
        assert mode == 0o600

    def test_tightens_permissions_of_preexisting_file(self, cache_path):
        cache_path.write_text("{}")
        cache_path.chmod(0o644)
        save_cached_creds({"auth_token": "tok", "id": "1"}, cache_path)
        assert stat.S_IMODE(cache_path.stat().st_mode) == 0o600

    def test_missing_file_returns_none(self, tmp_path):
        assert load_cached_creds(tmp_path / "nonexistent") is None

    def test_corrupt_file_returns_none(self, cache_path):
        cache_path.write_text("not json")
        assert load_cached_creds(cache_path) is None

    def test_incomplete_payload_returns_none(self, cache_path):
        cache_path.write_text(json.dumps({"auth_token": "tok"}))
        assert load_cached_creds(cache_path) is None


class TestNetrcCredentials:
    def test_reads_matching_machine(self, netrc_file):
        path = netrc_file("machine mobilevids\n\tlogin alice\n\tpassword secret\n")
        assert read_netrc_credentials(path) == ("alice", "secret")

    def test_missing_file_raises_authentication_error(self, tmp_path):
        with pytest.raises(AuthenticationError):
            read_netrc_credentials(tmp_path / "nonexistent")

    def test_absent_machine_entry_raises_authentication_error_not_typeerror(self, netrc_file):
        # Regression: netrc.authenticators() returns None for an unknown
        # machine, and the old code did `creds[0], creds[2]` on that None,
        # raising an opaque TypeError instead of the documented help text.
        path = netrc_file("machine some-other-site\n\tlogin alice\n\tpassword secret\n")
        with pytest.raises(AuthenticationError, match="mobilevids"):
            read_netrc_credentials(path)

    def test_malformed_netrc_raises_authentication_error(self, netrc_file):
        path = netrc_file("this is not valid netrc syntax {{{\n")
        with pytest.raises(AuthenticationError):
            read_netrc_credentials(path)

    def test_incomplete_entry_raises_authentication_error(self, netrc_file):
        path = netrc_file("machine mobilevids\n\tlogin alice\n")
        with pytest.raises(AuthenticationError, match="incomplete"):
            read_netrc_credentials(path)

    def test_machine_name_matches_documented_value(self, netrc_file):
        # Regression: the README told users to write "machine mobilevids-dl"
        # while the code looked up "mobilevids". They must agree.
        from mobilevids.define import NETRC_MACHINE

        assert NETRC_MACHINE == "mobilevids"
        path = netrc_file(f"machine {NETRC_MACHINE}\n\tlogin alice\n\tpassword secret\n")
        assert read_netrc_credentials(path) == ("alice", "secret")


class TestResolveCredentials:
    def test_prefers_explicit_arguments(self, netrc_file):
        netrc_file("machine mobilevids\n\tlogin netrc-user\n\tpassword netrc-pass\n")
        assert resolve_credentials("cli-user", "cli-pass") == ("cli-user", "cli-pass")

    def test_falls_back_to_environment(self, monkeypatch, tmp_path):
        monkeypatch.setenv("MOBILEVIDS_USERNAME", "env-user")
        monkeypatch.setenv("MOBILEVIDS_PASSWORD", "env-pass")
        assert resolve_credentials(netrc_path=tmp_path / "unused") == ("env-user", "env-pass")

    def test_falls_back_to_netrc(self, netrc_file, monkeypatch):
        monkeypatch.delenv("MOBILEVIDS_USERNAME", raising=False)
        monkeypatch.delenv("MOBILEVIDS_PASSWORD", raising=False)
        path = netrc_file("machine mobilevids\n\tlogin netrc-user\n\tpassword netrc-pass\n")
        assert resolve_credentials(netrc_path=path) == ("netrc-user", "netrc-pass")


class TestLogin:
    def test_success_returns_and_caches_credentials(self, session, requests_mock, cache_path):
        requests_mock.post(LOGIN_URL, json={"auth_token": "fake_token", "id": "12345"})
        creds = login(session, "user", "pass", cache_path)
        assert creds == Credentials("fake_token", "12345")
        assert load_cached_creds(cache_path) == creds

    def test_password_is_json_escaped_in_payload(self, session, requests_mock, cache_path):
        # A password containing a quote must not break out of the JSON payload.
        requests_mock.post(LOGIN_URL, json={"auth_token": "t", "id": "1"})
        login(session, 'user"name', 'pa"ss', cache_path)
        sent = requests_mock.last_request.text
        payload = json.loads(unquote_plus(sent.removeprefix("data=")))
        assert payload == {"Name": 'user"name', "Password": 'pa"ss'}

    def test_rejected_login_raises_authentication_error(self, session, requests_mock, cache_path):
        requests_mock.post(LOGIN_URL, json={"status": "-1", "message": "bad credentials"})
        with pytest.raises(AuthenticationError, match="bad credentials"):
            login(session, "user", "pass", cache_path)

    def test_non_json_response_raises_authentication_error(
        self, session, requests_mock, cache_path
    ):
        requests_mock.post(LOGIN_URL, text="<html>error</html>")
        with pytest.raises(AuthenticationError):
            login(session, "user", "pass", cache_path)

    def test_network_failure_raises_authentication_error(self, session, requests_mock, cache_path):
        requests_mock.post(LOGIN_URL, exc=requests.ConnectionError)
        with pytest.raises(AuthenticationError):
            login(session, "user", "pass", cache_path)


class TestGetCreds:
    def test_uses_valid_cached_credentials_without_logging_in(
        self, session, requests_mock, cache_path
    ):
        save_cached_creds({"auth_token": "cached", "id": "1"}, cache_path)
        requests_mock.get(GET_VIDEO_URL, json={"status": "1"})
        login_mock = requests_mock.post(LOGIN_URL, json={"auth_token": "new", "id": "2"})

        creds = get_creds(session, cache_path=cache_path)

        assert creds == Credentials("cached", "1")
        assert not login_mock.called

    def test_falls_back_to_login_when_cache_is_rejected(self, session, requests_mock, cache_path):
        save_cached_creds({"auth_token": "stale", "id": "1"}, cache_path)
        requests_mock.get(GET_VIDEO_URL, json={"status": "-1"})
        requests_mock.post(LOGIN_URL, json={"auth_token": "fresh", "id": "2"})

        creds = get_creds(session, "user", "pass", cache_path=cache_path)

        assert creds == Credentials("fresh", "2")

    def test_falls_back_to_login_when_no_cache_exists(self, session, requests_mock, tmp_path):
        requests_mock.post(LOGIN_URL, json={"auth_token": "fresh", "id": "2"})
        creds = get_creds(session, "user", "pass", cache_path=tmp_path / "missing")
        assert creds == Credentials("fresh", "2")

    def test_falls_back_to_login_when_cache_probe_fails(self, session, requests_mock, cache_path):
        save_cached_creds({"auth_token": "stale", "id": "1"}, cache_path)
        requests_mock.get(GET_VIDEO_URL, exc=requests.ConnectionError)
        requests_mock.post(LOGIN_URL, json={"auth_token": "fresh", "id": "2"})

        creds = get_creds(session, "user", "pass", cache_path=cache_path)

        assert creds == Credentials("fresh", "2")
