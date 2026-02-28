import typing
from http import HTTPStatus


class AuthError(Exception):
    def __init__(
        self,
        code: int = HTTPStatus.UNAUTHORIZED,
        msg: str = "",
        details: str = "",
        data_source_id: int = -1,
    ) -> None:

        if not msg:
            msg = HTTPStatus(code).phrase

        self.code = code
        self.msg = msg
        self.details = details
        self.data_source_id = data_source_id
