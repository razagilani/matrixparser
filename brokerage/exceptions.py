class MatrixError(Exception):
    """Generic error class."""


class DatabaseError(MatrixError):
    """Raised when we have a database-related problem"""


class ValidationError(MatrixError):
    pass
