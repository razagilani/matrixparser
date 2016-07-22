"""Miscellaneous helper functions/classes.

This module's name comes from the recommended project structure at
http://flask-restful.readthedocs.org/en/0.3.1/intermediate-usage.html#project-structure
If it gets big, it should become a multi-file module as shown there.
"""
from flask.ext.bcrypt import Bcrypt

_bcrypt = None

def get_bcrypt_object():
    global _bcrypt
    if _bcrypt is None:
        _bcrypt = Bcrypt()
    return _bcrypt
