class SearchError(RuntimeError):
    """Base class for paper-source failures."""


class TransientSearchError(SearchError):
    """A failure that may succeed if retried later."""


class PermanentSearchError(SearchError):
    """A failure that should not be retried blindly."""
