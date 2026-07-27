"""Resumable, parallel HTTP file transfer built on :mod:`requests`.

Replaces the unmaintained ``pypdl``/``wget`` pair. A transfer writes into a
sibling ``<name>.part`` file and is only renamed into place once complete, so an
interrupted run never leaves a truncated video looking like a finished one.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import unquote, urlsplit

import requests

from .define import CHUNK_SIZE, DEFAULT_SEGMENTS, REQUEST_TIMEOUT
from .errors import DownloadError

log = logging.getLogger(__name__)

FALLBACK_FILENAME = "download.mp4"

#: Everything outside this set is replaced, which keeps separators, NUL bytes,
#: shell metacharacters and Windows-reserved characters out of path components.
_UNSAFE_CHARS = re.compile(r"[^\w.() \[\]-]", re.ASCII)
_MAX_COMPONENT_LENGTH = 150


class DownloadInterrupted(DownloadError):
    """The user aborted the transfer."""


def sanitize_component(raw: str, fallback: str = "") -> str:
    """Reduce untrusted text to a single, safe path component.

    Server-supplied titles and URLs reach the filesystem, so percent-escapes are
    decoded *before* filtering (``%2f`` would otherwise smuggle in a separator)
    and the result can never be empty, ``.`` or ``..``.
    """
    decoded = unquote(raw).replace("\\", "/")
    cleaned = _UNSAFE_CHARS.sub("_", decoded.rsplit("/", 1)[-1])
    cleaned = cleaned.strip(" .")[:_MAX_COMPONENT_LENGTH].strip(" .")
    return cleaned or fallback


def filename_from_url(url: str, fallback: str = FALLBACK_FILENAME) -> str:
    """Derive a safe filename from ``url``'s path."""
    return sanitize_component(urlsplit(url).path, fallback)


class SegmentedDownloader:
    """Download one URL, using byte ranges in parallel when the server allows it."""

    def __init__(
        self,
        session: requests.Session,
        url: str,
        dest: Path,
        *,
        segments: int = DEFAULT_SEGMENTS,
        chunk_size: int = CHUNK_SIZE,
        timeout: tuple[int, int] = REQUEST_TIMEOUT,
        retries: int = 3,
    ) -> None:
        self.session = session
        self.url = url
        self.dest = dest
        self.segments = max(1, segments)
        self.chunk_size = chunk_size
        self.timeout = timeout
        self.retries = max(0, retries)
        self.part = dest.with_name(dest.name + ".part")
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._downloaded = 0
        self._total = 0
        self._last_report = 0.0

    def stop(self) -> None:
        """Ask every worker thread to abort; safe to call from a signal handler."""
        self._stop.set()

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()

    def run(self) -> Path:
        """Transfer the file and return its final path."""
        self.dest.parent.mkdir(parents=True, exist_ok=True)
        total, accepts_ranges = self._probe()
        self._total = total

        try:
            if total > 0 and accepts_ranges and self.segments > 1:
                self._download_segmented(total)
            else:
                self._download_single()
        except DownloadInterrupted:
            self.part.unlink(missing_ok=True)
            raise

        if self.stopped:
            self.part.unlink(missing_ok=True)
            raise DownloadInterrupted(f"Download of {self.dest.name} was interrupted")

        self.part.replace(self.dest)
        log.debug("Renamed %s to %s", self.part, self.dest)
        return self.dest

    def _probe(self) -> tuple[int, bool]:
        """Return the file size and whether the server honours byte ranges."""
        try:
            response = self.session.head(self.url, timeout=self.timeout, allow_redirects=True)
            if response.status_code >= 400:
                # Some hosts reject HEAD; fall back to a one-byte ranged GET.
                response = self.session.get(
                    self.url,
                    timeout=self.timeout,
                    headers={"Range": "bytes=0-0"},
                    stream=True,
                )
                response.close()
        except requests.RequestException as exc:
            raise DownloadError(f"Could not reach {self.url}: {exc}") from exc

        if response.status_code >= 400:
            raise DownloadError(f"Server returned HTTP {response.status_code} for {self.url}")

        content_range = response.headers.get("Content-Range", "")
        if response.status_code == 206 and "/" in content_range:
            size_text = content_range.rsplit("/", 1)[-1]
            total = int(size_text) if size_text.isdigit() else 0
            return total, True

        length = response.headers.get("Content-Length", "")
        total = int(length) if length.isdigit() else 0
        accepts_ranges = response.headers.get("Accept-Ranges", "none").lower() == "bytes"
        return total, accepts_ranges

    def _split(self, total: int) -> list[tuple[int, int]]:
        """Split ``total`` bytes into inclusive ``(start, end)`` ranges."""
        count = min(self.segments, total)
        size = total // count
        bounds = [(i * size, (i + 1) * size - 1) for i in range(count)]
        start, _ = bounds[-1]
        bounds[-1] = (start, total - 1)
        return bounds

    def _download_segmented(self, total: int) -> None:
        ranges = self._split(total)
        log.debug("Downloading %s in %d segments", self.dest.name, len(ranges))

        # Preallocate so each worker can seek to its own disjoint offset.
        with self.part.open("wb") as handle:
            handle.truncate(total)

        with ThreadPoolExecutor(max_workers=len(ranges)) as pool:
            futures = [pool.submit(self._fetch_range, start, end) for start, end in ranges]
            errors: list[BaseException] = []
            for future in futures:
                try:
                    future.result()
                except BaseException as exc:
                    # Stop the siblings so a failure does not wait out the rest.
                    self.stop()
                    errors.append(exc)
        if errors:
            raise errors[0]

    def _fetch_range(self, start: int, end: int) -> None:
        """Fetch ``start``-``end`` into the preallocated part file, retrying gaps."""
        position = start
        attempt = 0
        while position <= end and not self.stopped:
            before = position
            try:
                position = self._stream_into(position, end)
            except (requests.RequestException, OSError) as exc:
                if attempt >= self.retries:
                    raise DownloadError(
                        f"Failed to download bytes {before}-{end} of {self.dest.name}: {exc}"
                    ) from exc
                attempt += 1
                self._backoff(attempt)
                continue

            if position > before:
                attempt = 0
            elif attempt >= self.retries:
                raise DownloadError(
                    f"Server stopped sending data at byte {position} of {self.dest.name}"
                )
            else:
                attempt += 1
                self._backoff(attempt)

    def _stream_into(self, position: int, end: int) -> int:
        """Stream one ranged response into the part file; return the new offset."""
        headers = {"Range": f"bytes={position}-{end}"}
        with self.session.get(
            self.url, headers=headers, stream=True, timeout=self.timeout
        ) as response:
            if response.status_code != 206:
                raise DownloadError(
                    f"Expected HTTP 206 for a ranged request, got {response.status_code}"
                )
            with self.part.open("r+b") as handle:
                handle.seek(position)
                for chunk in response.iter_content(self.chunk_size):
                    if self.stopped:
                        break
                    if not chunk:
                        continue
                    handle.write(chunk)
                    position += len(chunk)
                    self._advance(len(chunk))
        return position

    def _download_single(self) -> None:
        """Single-connection transfer, resuming an existing part file when possible."""
        position = self.part.stat().st_size if self.part.exists() else 0
        attempt = 0
        while not self.stopped:
            before = position
            try:
                position, complete = self._stream_append(position)
            except (requests.RequestException, OSError) as exc:
                if attempt >= self.retries:
                    raise DownloadError(f"Failed to download {self.dest.name}: {exc}") from exc
                attempt += 1
                self._backoff(attempt)
                continue

            if complete:
                return
            if position > before:
                attempt = 0
            elif attempt >= self.retries:
                raise DownloadError(
                    f"Server stopped sending data at byte {position} of {self.dest.name}"
                )
            else:
                attempt += 1
                self._backoff(attempt)

    def _stream_append(self, position: int) -> tuple[int, bool]:
        """Append one response body to the part file.

        Returns the new offset and whether the transfer finished. A server that
        ignores our ``Range`` header replies ``200`` with the whole body, so the
        part file is restarted from zero rather than being corrupted.
        """
        headers = {"Range": f"bytes={position}-"} if position else {}
        with self.session.get(
            self.url, headers=headers, stream=True, timeout=self.timeout
        ) as response:
            if response.status_code >= 400:
                raise DownloadError(f"Server returned HTTP {response.status_code} for {self.url}")
            if position and response.status_code != 206:
                log.debug("Server ignored Range header; restarting %s", self.dest.name)
                position = 0
                with self._lock:
                    self._downloaded = 0
            mode = "ab" if position else "wb"
            with self.part.open(mode) as handle:
                for chunk in response.iter_content(self.chunk_size):
                    if self.stopped:
                        return position, False
                    if not chunk:
                        continue
                    handle.write(chunk)
                    position += len(chunk)
                    self._advance(len(chunk))
        return position, True

    def _backoff(self, attempt: int) -> None:
        """Sleep between retries, but stay responsive to :meth:`stop`."""
        delay = min(2 ** (attempt - 1), 8)
        log.debug("Retry %d for %s in %ss", attempt, self.dest.name, delay)
        self._stop.wait(delay)

    def _advance(self, count: int) -> None:
        with self._lock:
            self._downloaded += count
            now = time.monotonic()
            if now - self._last_report < 1.5:
                return
            self._last_report = now
            downloaded = self._downloaded
        if self._total:
            percent = downloaded * 100 / self._total
            log.info(
                "  %s: %5.1f%% (%s / %s)",
                self.dest.name,
                percent,
                _human(downloaded),
                _human(self._total),
            )
        else:
            log.info("  %s: %s downloaded", self.dest.name, _human(downloaded))


def _human(size: float) -> str:
    """Format a byte count for humans."""
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024 or unit == "GiB":
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GiB"  # pragma: no cover - loop always returns
