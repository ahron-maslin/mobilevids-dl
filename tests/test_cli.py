"""End-to-end CLI checks, driven in-process through mobilevids.dispatcher.main.

The previous version shelled out to the installed ``mobilevids-dl`` console
script, which meant these tests only worked after a real `pip install`, and its
version check asserted `returncode != 127` -- true even when the program
crashed on startup, which is a tautology rather than a test.
"""

from __future__ import annotations

import pytest

from mobilevids import __VERSION__
from mobilevids.dispatcher import main
from mobilevids.options import build_parser


class TestHelp:
    def test_help_exits_zero_and_describes_the_program(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            build_parser().parse_args(["--help"])
        assert excinfo.value.code == 0
        assert "Mobilevids Downloader script" in capsys.readouterr().out


class TestVersion:
    def test_version_flag_prints_current_version(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            build_parser().parse_args(["--version"])
        assert excinfo.value.code == 0
        assert __VERSION__ in capsys.readouterr().out


class TestMainMissingCredentials:
    def test_no_credentials_available_fails_cleanly(
        self, tmp_path, monkeypatch, capsys, cache_path
    ):
        monkeypatch.setattr("mobilevids.network.AUTH_TOKEN_CACHE", cache_path)
        monkeypatch.delenv("MOBILEVIDS_USERNAME", raising=False)
        monkeypatch.delenv("MOBILEVIDS_PASSWORD", raising=False)

        exit_code = main(["-n", str(tmp_path / "no-such-netrc"), "-o", str(tmp_path), "x"])

        assert exit_code == 1
        assert "Traceback" not in capsys.readouterr().err
