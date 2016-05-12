class BillingError(Exception):
    """Generic error class."""


class DatabaseError(BillingError):
    """Raised when we have a database-related problem"""


class ValidationError(BillingError):
    pass
