from __future__ import annotations

import pytest

from mobilevids.download import (
    DownloadInterrupted,
    SegmentedDownloader,
    filename_from_url,
    sanitize_component,
)
from mobilevids.errors import DownloadError
from tests.conftest import file_server


class TestSanitizeComponent:
    def test_keeps_ordinary_names(self):
        assert sanitize_component("Movie Title (2020).mp4") == "Movie Title (2020).mp4"

    def test_strips_path_separators(self):
        # Regression: a server-controlled title/filename used to be joined
        # into a path unsanitized, allowing traversal outside download_dir.
        assert "/" not in sanitize_component("../../etc/passwd")
        assert ".." not in sanitize_component("../../etc/passwd")

    def test_decodes_percent_escapes_before_filtering(self):
        # A raw "%2f" must not survive as a literal slash after filtering.
        assert "/" not in sanitize_component("evil%2f..%2f..%2fname")

    def test_empty_input_uses_fallback(self):
        assert sanitize_component("", fallback="fallback.bin") == "fallback.bin"

    def test_dot_only_input_uses_fallback(self):
        assert sanitize_component("...", fallback="fallback.bin") == "fallback.bin"


class TestFilenameFromUrl:
    def test_extracts_basename(self):
        assert filename_from_url("https://mobilevids.org/media/videos/movie.mp4") == "movie.mp4"

    def test_falls_back_when_path_has_no_basename(self):
        assert filename_from_url("https://mobilevids.org/") == "download.mp4"


class TestSegmentedDownloaderSingle:
    def test_downloads_full_content_without_range_support(self, session, requests_mock, tmp_path):
        data = b"x" * 5000
        head_cb, get_cb = file_server(data, accept_ranges=False)
        requests_mock.head("http://x/video.mp4", content=head_cb)
        requests_mock.get("http://x/video.mp4", content=get_cb)

        dest = tmp_path / "video.mp4"
        SegmentedDownloader(session, "http://x/video.mp4", dest, segments=4).run()

        assert dest.read_bytes() == data
        assert not dest.with_name(dest.name + ".part").exists()

    def test_resumes_partial_download_when_ranges_supported(self, session, requests_mock, tmp_path):
        data = bytes(range(256)) * 20
        head_cb, get_cb = file_server(data, accept_ranges=True)
        requests_mock.head("http://x/video.mp4", content=head_cb)
        requests_mock.get("http://x/video.mp4", content=get_cb)

        dest = tmp_path / "video.mp4"
        part = dest.with_name(dest.name + ".part")
        part.write_bytes(data[:1000])

        SegmentedDownloader(session, "http://x/video.mp4", dest, segments=1).run()

        assert dest.read_bytes() == data

    def test_server_ignoring_range_header_restarts_cleanly(self, session, requests_mock, tmp_path):
        # Regression: naively appending to a stale .part file when a server
        # ignores Range and replies 200 with the full body would duplicate
        # the already-downloaded prefix. The downloader must detect this and
        # restart instead of corrupting the output.
        data = b"y" * 2000
        head_cb, get_cb = file_server(data, accept_ranges=False)
        requests_mock.head("http://x/video.mp4", content=head_cb)
        requests_mock.get("http://x/video.mp4", content=get_cb)

        dest = tmp_path / "video.mp4"
        part = dest.with_name(dest.name + ".part")
        part.write_bytes(data[:500])

        SegmentedDownloader(session, "http://x/video.mp4", dest, segments=1).run()

        assert dest.read_bytes() == data


class TestSegmentedDownloaderMultiSegment:
    def test_downloads_full_content_across_segments(self, session, requests_mock, tmp_path):
        data = bytes(i % 256 for i in range(10_000))
        head_cb, get_cb = file_server(data, accept_ranges=True)
        requests_mock.head("http://x/video.mp4", content=head_cb)
        requests_mock.get("http://x/video.mp4", content=get_cb)

        dest = tmp_path / "video.mp4"
        SegmentedDownloader(session, "http://x/video.mp4", dest, segments=4).run()

        assert dest.read_bytes() == data


class TestSegmentedDownloaderStop:
    def test_stop_removes_part_file_and_raises_interrupted(self, session, requests_mock, tmp_path):
        data = b"z" * 5000
        head_cb, get_cb = file_server(data, accept_ranges=False)
        requests_mock.head("http://x/video.mp4", content=head_cb)

        def get_cb_that_stops(request, context):
            downloader.stop()
            return get_cb(request, context)

        requests_mock.get("http://x/video.mp4", content=get_cb_that_stops)

        dest = tmp_path / "video.mp4"
        downloader = SegmentedDownloader(session, "http://x/video.mp4", dest, segments=1)

        with pytest.raises(DownloadInterrupted):
            downloader.run()

        assert not dest.exists()
        assert not dest.with_name(dest.name + ".part").exists()


class TestSegmentedDownloaderErrors:
    def test_http_error_status_raises_download_error(self, session, requests_mock, tmp_path):
        requests_mock.head("http://x/video.mp4", status_code=404)
        requests_mock.get("http://x/video.mp4", status_code=404)
        dest = tmp_path / "video.mp4"
        with pytest.raises(DownloadError):
            SegmentedDownloader(session, "http://x/video.mp4", dest).run()
