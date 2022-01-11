import importlib
import os
from pathlib import Path

from pypiserver_update.application_settings import ApplicationSettings

"""
This is the command line argument handling.
"""

APP_PACKAGE = 'pypiserver_update'
app_module = importlib.import_module(APP_PACKAGE)
APP_DESCRIPTION = app_module.__doc__

PYPI_SIMPLE_URL = "https://pypi.org/simple/"


class PypiServerUpdateSettings(ApplicationSettings):
    """
    Usage::

        with PypiServerUpdateSettings() as settings:
        try:
            app.execute(self, settings)
            exit(0)
        except ArgumentError as ex:
            error(str(ex))
            exit(1)
    """
    PACKAGES_DIR = "/srv/pypiserver/packages"

    HELP = {
        'PypiServerUpdate': APP_DESCRIPTION,

        'options_group': 'Application options',
        'packages_dir': f'The path to the pypiserver package\'s directory (default={PACKAGES_DIR})',
        'execute_pip_downloads': 'Run the pip commands to download new packages.  (default=False)',
        "pypi_simple_url": f'The URL to pypi\'s simple API.  (default={PYPI_SIMPLE_URL})',

        'info_group': '',
        'version': "Show PypiServerUpdate's version.",
    }

    def __init__(self):
        super().__init__('PypiServerUpdate', APP_PACKAGE, ['PypiServerUpdate'], self.HELP)

    def _cli_options(self, parser, defaults):
        """
        Adds application specific arguments to the parser.

        :param parser: the argument parser with --conf_file already added.
        :type parser: argparse.ArgumentParser
        """

        def dir_path(string):
            if os.path.isdir(string):
                return string
            else:
                raise NotADirectoryError(string)

        options_group = parser.add_argument_group(title='Application Options', description=self._help['options_group'])
        options_group.add_argument('--packages_dir', type=dir_path, metavar='PATH', help=self._help['packages_dir'])
        options_group.add_argument('-e', '--execute_pip_downloads', dest='execute_pip_downloads', action='store_true',
                                   help=self._help['execute_pip_downloads'])
        options_group.add_argument('--pypi_simple_url', type=str, metavar='URL', dest='pypi_simple_url',
                                   default=PYPI_SIMPLE_URL, help=self._help['pypi_simple_url'])

        info_group = parser.add_argument_group(title='Informational Commands', description=self._help['info_group'])
        info_group.add_argument('--version', dest='version', action='store_true', help=self._help['version'])

    def _cli_validate(self, settings, remaining_argv):
        """
        Verify we have required options for commands.

        :param settings: the settings object returned by ArgumentParser.parse_args()
        :type settings: argparse.Namespace
        :return: the error message if any
        :rtype: str or None
        """
        if not settings.packages_dir:
            return "--packages_dir is required!"
        if not os.path.isdir(settings.packages_dir):
            return f"--packages_dir {settings.packages_dir} is not a directory!"
        settings.packages_dir = Path(settings.packages_dir)
        return None
