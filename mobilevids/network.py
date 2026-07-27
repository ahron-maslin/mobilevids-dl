"""HTTP session management, authentication and JSON API reads."""

from __future__ import annotations

import json
import logging
import netrc
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .define import (
    AUTH_TOKEN_CACHE,
    ENV_PASSWORD,
    ENV_USERNAME,
    GET_VIDEO_URL,
    HEADERS,
    LOGIN_URL,
    NETRC_FILE_PATH,
    NETRC_MACHINE,
    REQUEST_TIMEOUT,
)
from .errors import ApiError, AuthenticationError

log = logging.getLogger(__name__)

_NETRC_HELP = f"""No usable credentials found. Provide them in any of these ways:

  * pass --username and --password on the command line
  * set the {ENV_USERNAME} and {ENV_PASSWORD} environment variables
  * add a machine entry to {NETRC_FILE_PATH}:

        machine {NETRC_MACHINE}
            login YOUR_USERNAME
            password YOUR_PASSWORD
"""


@dataclass(frozen=True, slots=True)
class Credentials:
    """An authenticated API session identity."""

    auth_token: str
    user_id: str


def session_init() -> requests.Session:
    """Create a session preloaded with the headers the API expects."""
    session = requests.Session()
    session.headers.update(HEADERS)
    log.debug("Created session")
    return session


def get_json(
    session: requests.Session,
    url: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """GET ``url`` and decode the JSON body.

    ``params`` is passed to requests so values are URL-encoded rather than
    interpolated into the query string.
    """
    try:
        response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ApiError(f"Request to {url} failed: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise ApiError(
            f"{url} returned {response.status_code} with a non-JSON body "
            f"({response.headers.get('Content-Type', 'unknown type')})"
        ) from exc

    if not isinstance(payload, dict):
        raise ApiError(f"{url} returned {type(payload).__name__}, expected a JSON object")

    log.debug("Response from %s: %s", url, payload)
    return payload


def save_cached_creds(login_info: dict[str, Any], path: Path | None = None) -> None:
    """Cache the login response, readable only by the current user.

    The file holds a bearer token, so it is created with mode ``0600`` and any
    pre-existing file has its permissions tightened.
    """
    path = path or AUTH_TOKEN_CACHE
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as cache_file:
        json.dump(login_info, cache_file)
    path.chmod(0o600)
    log.debug("Cached credentials in %s", path)


def load_cached_creds(path: Path | None = None) -> Credentials | None:
    """Return cached credentials, or ``None`` if absent or unreadable."""
    path = path or AUTH_TOKEN_CACHE
    try:
        with path.open(encoding="utf-8") as cache_file:
            cached = json.load(cache_file)
    except (OSError, ValueError) as exc:
        log.debug("Ignoring unusable credential cache %s: %s", path, exc)
        return None

    token, user_id = cached.get("auth_token"), cached.get("id")
    if not token or not user_id:
        log.debug("Credential cache %s is missing auth_token/id", path)
        return None
    return Credentials(str(token), str(user_id))


def _cached_creds_are_valid(session: requests.Session, creds: Credentials) -> bool:
    """Probe the API to see whether a cached token is still accepted."""
    try:
        payload = get_json(
            session,
            GET_VIDEO_URL,
            {"user_id": creds.user_id, "token": creds.auth_token, "id": "1"},
        )
    except ApiError as exc:
        log.debug("Could not validate cached credentials: %s", exc)
        return False
    return str(payload.get("status", "-1")).strip() != "-1"


def read_netrc_credentials(path: Path | None = None) -> tuple[str, str]:
    """Read the username and password for :data:`NETRC_MACHINE` from ``path``."""
    path = path or NETRC_FILE_PATH
    try:
        authenticators = netrc.netrc(str(path)).authenticators(NETRC_MACHINE)
    except FileNotFoundError as exc:
        raise AuthenticationError(_NETRC_HELP) from exc
    except (OSError, netrc.NetrcParseError) as exc:
        raise AuthenticationError(f"Could not read {path}: {exc}") from exc

    # authenticators() returns None when the machine entry is absent.
    if authenticators is None:
        raise AuthenticationError(
            f"{path} has no 'machine {NETRC_MACHINE}' entry.\n\n{_NETRC_HELP}"
        )

    login, _, password = authenticators
    if not login or not password:
        raise AuthenticationError(f"The '{NETRC_MACHINE}' entry in {path} is incomplete")
    log.debug("Loaded credentials for machine %r from %s", NETRC_MACHINE, path)
    return login, password


def login(
    session: requests.Session,
    username: str,
    password: str,
    cache_path: Path | None = None,
) -> Credentials:
    """Exchange a username and password for an API token."""
    # json.dumps escapes quotes and backslashes, and requests URL-encodes the
    # form body, so credentials cannot break out of the payload.
    payload = {"data": json.dumps({"Name": username, "Password": password})}
    log.debug("Logging in as %s", username)

    try:
        response = session.post(LOGIN_URL, data=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise AuthenticationError(f"Login request failed: {exc}") from exc

    try:
        login_info = response.json()
    except ValueError as exc:
        raise AuthenticationError("Login response was not valid JSON") from exc

    token, user_id = login_info.get("auth_token"), login_info.get("id")
    if not token or not user_id:
        message = login_info.get("message") or login_info.get("status") or "unknown error"
        raise AuthenticationError(f"Login was rejected: {message}")

    save_cached_creds(login_info, cache_path)
    log.info("Successfully logged in")
    return Credentials(str(token), str(user_id))


def resolve_credentials(
    username: str | None = None,
    password: str | None = None,
    netrc_path: Path | None = None,
) -> tuple[str, str]:
    """Find credentials from arguments, the environment, then the netrc file."""
    username = username or os.environ.get(ENV_USERNAME)
    password = password or os.environ.get(ENV_PASSWORD)
    if username and password:
        return username, password

    netrc_username, netrc_password = read_netrc_credentials(netrc_path or NETRC_FILE_PATH)
    return username or netrc_username, password or netrc_password


def get_creds(
    session: requests.Session,
    username: str | None = None,
    password: str | None = None,
    netrc_path: Path | None = None,
    cache_path: Path | None = None,
) -> Credentials:
    """Return usable credentials, reusing the cached token when it still works."""
    cached = load_cached_creds(cache_path)
    if cached and _cached_creds_are_valid(session, cached):
        log.info("Using cached credentials")
        return cached

    resolved_username, resolved_password = resolve_credentials(username, password, netrc_path)
    return login(session, resolved_username, resolved_password, cache_path)
