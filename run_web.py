#!/usr/bin/env python
"""Entry point to run web UI.
Can also be run with gunicorn with "gunicorn run_web"
"""
from brokerage import initialize
from billentry import application
initialize()

if __name__ == '__main__':
    application.run(debug=True)
