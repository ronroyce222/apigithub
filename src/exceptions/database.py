"""database.py: Custom exceptions for database operations."""


class DatabaseHealthException(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class DatabaseUpsertException(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class DatabaseGeneralException(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class DatabaseFetchException(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class DatabaseConnectionException(Exception):
    def __init__(self, *args):
        super().__init__(*args)
