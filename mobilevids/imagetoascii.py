"""Render poster thumbnails as terminal ASCII art."""

from __future__ import annotations

import logging

import ascii_magic

log = logging.getLogger(__name__)

DEFAULT_COLUMNS = 30


def image_to_ascii(image_url: str, columns: int = DEFAULT_COLUMNS) -> None:
    """Print the image at ``image_url`` as ASCII art.

    Poster art is decoration around search results, so any failure (an
    unreachable URL, an image Pillow cannot decode) is logged and swallowed
    rather than aborting the search listing.
    """
    try:
        art = ascii_magic.from_url(image_url)
    except Exception as exc:
        log.debug("Could not fetch poster %s: %s", image_url, exc)
        log.warning("Could not render poster art for %s", image_url)
        return

    try:
        art.to_terminal(columns=columns)
    except Exception as exc:
        log.debug("Could not render poster %s: %s", image_url, exc)
