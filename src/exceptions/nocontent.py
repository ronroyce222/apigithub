from http import HTTPStatus


class NoContentException(Exception):
    """Exception for HTTP 204 No Content responses."""

    def __init__(self) -> None:
        """Initialize with NO_CONTENT status."""
        super().__init__(HTTPStatus.NO_CONTENT)
