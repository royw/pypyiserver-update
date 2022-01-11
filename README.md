pypyserver-update
=================

pypi.org has turned off XML-RPC support in Warehouse due to severe abuse.

pypi.org recommends using the JSON API.

A side effect is that pypiserver's update command (pypiserver -U) no longer works.

This utility simply updates the local pypiserver's packages to the latest available on pypi.org
using the JSON API and pip.

Usage:  pypiserver_update_main.py --packages_dir path_to_pypiserver/packages

Development
-----------

Poetry is recommended for the development environment.

➤ poetry install
➤ poetry run main --help
➤ poetry run main --packages_dir $HOME/projects/pypiserver-update/packages

