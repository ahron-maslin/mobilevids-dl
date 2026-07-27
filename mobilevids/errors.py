"""Exception hierarchy.

Every failure the CLI can report to a user is one of these, so ``dispatcher.main``
can print a short message instead of a traceback.
"""

from __future__ import annotations


class MobileVidsError(Exception):
    """Base class for all errors raised by this package."""


class AuthenticationError(MobileVidsError):
    """Credentials are missing, malformed or rejected by the API."""


class ApiError(MobileVidsError):
    """The API was reachable but returned an unusable response."""


class NoVideoFoundError(MobileVidsError):
    """No downloadable source exists for the requested title."""


class DownloadError(MobileVidsError):
    """A video transfer failed and could not be recovered by retrying."""
