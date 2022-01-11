"""
pypi.org has turned off XML-RPC support in Warehouse due to severe abuse.

pypi.org's recommendation is to use the JSON API.

A side-effect is that pypiserver's update command (pypiserver -U) no longer works.

This utility simply updates the local pypiserver's packages to the latest available on pypi.org
using the JSON API.

Usage:  pypiserver_update_main.py --packages_dir path_to_pypiserver/packages
"""

__version__ = '0.1.0'
