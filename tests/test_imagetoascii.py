from __future__ import annotations

from unittest.mock import MagicMock

from mobilevids.imagetoascii import image_to_ascii


class TestImageToAscii:
    def test_renders_to_terminal(self, monkeypatch):
        art = MagicMock()
        monkeypatch.setattr("mobilevids.imagetoascii.ascii_magic.from_url", lambda url: art)

        image_to_ascii("https://example.com/poster.jpg", columns=40)

        art.to_terminal.assert_called_once_with(columns=40)

    def test_fetch_failure_does_not_raise(self, monkeypatch, caplog):
        # Regression: ascii_magic.to_terminal() does not exist on the pinned
        # 2.x API (the old code called it as a bare module function), so any
        # -a/--ascii search crashed. Poster art is decoration, so failures to
        # fetch or render it must never propagate out of a search listing.
        caplog.set_level("WARNING")

        def boom(url):
            raise ValueError("bad image")

        monkeypatch.setattr("mobilevids.imagetoascii.ascii_magic.from_url", boom)

        image_to_ascii("https://example.com/broken.jpg")

        assert "Could not render poster art" in caplog.text

    def test_render_failure_does_not_raise(self, monkeypatch):
        art = MagicMock()
        art.to_terminal.side_effect = ValueError("bad terminal")
        monkeypatch.setattr("mobilevids.imagetoascii.ascii_magic.from_url", lambda url: art)

        image_to_ascii("https://example.com/poster.jpg")
