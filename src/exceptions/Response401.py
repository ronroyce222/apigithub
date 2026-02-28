from pydantic import BaseModel


class ResponseModel401(BaseModel):
    status_code: int
    message: str
