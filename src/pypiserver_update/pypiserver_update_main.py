#!/bin/env python

import logging

from pypiserver_update.pypiserver_update_settings import PypiServerUpdateSettings
from pypiserver_update.pypiserver_update_app import PypiServerUpdateApp

"""
This is the main entry point for the pypiserver package update utility
"""

logging.basicConfig(level=logging.INFO)


def main() -> int:
    """ update the pypiserver packages
    """
    with PypiServerUpdateSettings() as settings:
        return PypiServerUpdateApp(settings).execute()


if __name__ == '__main__':
    exit(main())
