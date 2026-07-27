"""Shared fixtures.

Every fixture that touches the filesystem is rooted in ``tmp_path``: the previous
suite renamed the developer's real ``~/.mvdl_auth_token`` out of the way, which
destroyed live credentials whenever a test aborted midway.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pytest
import requests

from mobilevids.network import Credentials, session_init

RANGE_RE = re.compile(r"bytes=(\d+)-(\d*)")


@pytest.fixture
def session() -> requests.Session:
    return session_init()


@pytest.fixture
def credentials() -> Credentials:
    return Credentials(auth_token="test-token", user_id="42")


@pytest.fixture
def cache_path(tmp_path: Path) -> Path:
    return tmp_path / "auth_token_cache"


@pytest.fixture
def netrc_file(tmp_path: Path) -> Callable[[str], Path]:
    """Return a factory that writes a netrc file and returns its path."""

    def _write(contents: str) -> Path:
        path = tmp_path / "netrc"
        path.write_text(contents, encoding="utf-8")
        path.chmod(0o600)
        return path

    return _write


def file_server(
    data: bytes, *, accept_ranges: bool = True
) -> tuple[Callable[..., bytes], Callable[..., bytes]]:
    """Build ``(head, get)`` requests-mock callbacks serving ``data``.

    The GET callback honours ``Range`` when ``accept_ranges`` is set, and
    otherwise replies ``200`` with the whole body -- the behaviour that makes a
    naive resume corrupt the output file.
    """

    def head_callback(request: object, context: object) -> bytes:
        context.headers["Content-Length"] = str(len(data))  # type: ignore[attr-defined]
        context.headers["Accept-Ranges"] = "bytes" if accept_ranges else "none"  # type: ignore[attr-defined]
        return b""

    def get_callback(request: object, context: object) -> bytes:
        requested = request.headers.get("Range")  # type: ignore[attr-defined]
        match = RANGE_RE.fullmatch(requested or "")
        if match and accept_ranges:
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else len(data) - 1
            end = min(end, len(data) - 1)
            context.status_code = 206  # type: ignore[attr-defined]
            context.headers["Content-Range"] = f"bytes {start}-{end}/{len(data)}"  # type: ignore[attr-defined]
            return data[start : end + 1]
        context.status_code = 200  # type: ignore[attr-defined]
        return data

    return head_callback, get_callback
