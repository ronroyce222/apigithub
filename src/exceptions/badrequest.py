class BadRequestException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class MissingAPIVersion(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class InvalidAPIVersion(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class MissingJWTToken(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

