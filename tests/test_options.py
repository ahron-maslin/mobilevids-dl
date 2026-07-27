from __future__ import annotations

import pytest

from mobilevids.options import build_parser, options_parser


class TestBuildParser:
    def test_help_mentions_description(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            build_parser().parse_args(["--help"])
        assert excinfo.value.code == 0
        assert "Mobilevids Downloader script" in capsys.readouterr().out

    def test_version_flag_prints_version(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            build_parser().parse_args(["--version"])
        assert excinfo.value.code == 0
        assert "mobilevids-dl" in capsys.readouterr().out


class TestOptionsParser:
    def test_episode_without_tv_and_season_is_rejected(self, capsys):
        with pytest.raises(SystemExit):
            options_parser(["-e", "1"])
        assert "requires both -t/--tv and -s/--season" in capsys.readouterr().err

    def test_season_without_tv_is_rejected(self, capsys):
        with pytest.raises(SystemExit):
            options_parser(["-s", "1"])
        assert "requires -t/--tv" in capsys.readouterr().err

    def test_zero_segments_is_rejected(self, capsys):
        with pytest.raises(SystemExit):
            options_parser(["--segments", "0"])
        assert "--segments must be at least 1" in capsys.readouterr().err

    def test_full_episode_selection_is_accepted(self):
        args = options_parser(["-t", "5", "-s", "1", "-e", "2"])
        assert (args.tv, args.season, args.episode) == ("5", "1", "2")

    def test_defaults_are_sane(self):
        args = options_parser([])
        assert args.search is None
        assert args.segments >= 1
        assert args.ascii is False
