import argparse
import json
import logging
import re
import shlex
import subprocess
from pathlib import Path
from typing import Set, Any, List, Dict, Optional, Tuple

import requests
from versio.version import Version
from versio.version_scheme import Pep440VersionScheme

from pypiserver_update.graceful_interrupt_handler import GracefulInterruptHandler


"""
This is the object responsible for downloading new versions of packages already in packages_dir from pypi.org.

This uses the JSON API. 

Uses pip to download updates just like pypiserver -U, optionally running pip if -e is used.
"""


# noinspection PyMethodMayBeStatic
class PypiServerUpdateApp(object):
    def __init__(self, settings: argparse.Namespace):
        self.settings = settings

    def execute(self) -> int:
        """
        This is the primary execution loop that:
        * find the local packages and versions and package names
        * find the latest local version for each package
        * downloads newer packages
        Note that ^C can safely be used to abort the script using the GracefulInterruptHandler

        :return: the exit code (0 on success)
        """
        with GracefulInterruptHandler() as handler:
            local_packages = self._findLocalPackages(self.settings.packages_dir)
            local_versions = self._findLocalPackageVersions(local_packages)
            package_names = set(local_versions.keys())
            if handler.interrupted:
                return 1
            package_meta = self._findPackageMeta(package_names)
            if handler.interrupted:
                return 1
            latest_packages = self._findLatestLocalPackages(package_meta)
            if handler.interrupted:
                return 1

            return self._downloadNewerPackages(current_packages=local_packages,
                                               current_versions=local_versions,
                                               latest_packages=latest_packages,
                                               handler=handler)

    def _findLocalPackages(self, packages_dir: Path) -> Set[Path]:
        """
        Get the set of package paths for .tar.gz and .whl packages in the given packages_dir.

        :param packages_dir:  local package directory
        :return: set of Path to packages in the local package directory
        """
        return set(packages_dir.glob("*.whl")).union(set(packages_dir.glob("*.tar.gz")))

    def _normalizePackageName(self, name: str) -> str:
        """
        Normalize package names per PEP 503 (https://www.python.org/dev/peps/pep-0503/)

        :param name:  The package name
        :return: the normalized package name
        """
        return re.sub(r"[-]", '_', name)

    def _findLocalPackageVersions(self, local_packages: Set[Path]) -> Dict[str, List[str]]:
        """
        Finds the local packages and a list of their versions and builds a dictionary

        :param local_packages: set of local package Paths
        :return: dictionary with normalized package name strings as the key and a list of versions as strings
        for the package as the dictionary values.
        """
        def parse(name_: str) -> Tuple[Optional[str], Optional[str]]:
            """
            Given a local package filename (from Path.name), extract the package name and version.

            :param name_: the base filename of the package
            :return: a tuple containing the package name and version strings
            """
            match = re.match(r"(.*?)-(\d[.\da-z]*?)[.-]\D", name_)
            if match:
                return self._normalizePackageName(match.group(1)), match.group(2)
            return None, None

        local_versions: Dict[str, List[str]] = {}
        for pkg in local_packages:
            (name, version) = parse(pkg.name)
            if name and version:
                if name not in local_versions:
                    local_versions[name] = []
                local_versions[name].append(version)
        return local_versions

    def _findPackageMeta(self, package_names: Set[str]) -> Set[requests.Response]:
        """
        Use pypi's JSON API to get the index information for the set of packages.

        Note, one requests session is used for all of the requests.get calls.

        :param package_names:
        :return: the set of JSON API responses
        """
        session = requests.Session()
        responses = set()
        for name in package_names:
            url = f"https://pypi.org/pypi/{name}/json"
            try:
                resp = session.get(url)
                resp.raise_for_status()
                responses.add(resp)
            except requests.exceptions.HTTPError as ex:
                logging.error(f"Error getting {url} - {str(ex)}")
        session.close()
        return responses

    def _findLatestLocalPackages(self, package_meta: Set[requests.Response]) -> List[Dict[str, str]]:
        """
        Find the latest versions of the packages.  Ignore any release versions that are
        not PEP 440 compliant.

        :param package_meta:  This is the requests.response from the JSON API calls for all of the packages
        :return: a set of tuples containing the filename and url for the latest package
        """
        latest = list()
        for resp in package_meta:
            try:
                meta = resp.json()
                versions = list()
                for v in meta['releases'].keys():
                    # noinspection PyProtectedMember
                    if Pep440VersionScheme._is_match(v):
                        versions.append(v)
                try:
                    latest_release = str(sorted([Version(v) for v in versions])[-1])
                    for pkg in meta['releases'][latest_release]:
                        latest.append({
                            "package_name": self._normalizePackageName(meta['info']['name']),
                            "filename": pkg['filename'],
                            "url": pkg['url'],
                            "latest_version": latest_release
                        })
                except Exception as ex:
                    logging.error(f"{str(ex)} - {str(meta['releases'])}")
            except json.decoder.JSONDecodeError as ex:
                raise ex
        return latest

    def _downloadNewerPackages(self,
                               current_packages: Set[Path],
                               current_versions: Dict[str, List[str]],
                               latest_packages: List[Any],
                               handler: GracefulInterruptHandler) -> int:
        """
        Download the latest packages if they do not already exist locally.

        :param current_packages:  set of the current packages
        :param latest_packages:  set of the latest packages
        :param handler: the ^C GracefulInterruptHandler
        :return: exit code of 0 (true)
        """
        unique_set = set()
        package_names = set([pkg.name for pkg in current_packages])
        for pkg in latest_packages:
            filename = pkg['filename']
            if filename not in package_names:
                try:
                    if handler.interrupted:
                        return 1
                    package_name = pkg['package_name']
                    # noinspection PyProtectedMember
                    current_version = str(sorted([Version(v) for v in current_versions[package_name]
                                                  if Pep440VersionScheme._is_match(v)])[-1])
                    latest_version = pkg['latest_version']
                    if Version(current_version) < Version(latest_version):
                        unique_set.add(f"{package_name}|{current_version}|{latest_version}")
                except Exception as ex:
                    logging.error(f"Failed to download {filename} - {str(ex)}")

        for value in unique_set:
            values = value.split('|')
            self._pip_download_file(package_name=values[0],
                                    current_version=values[1],
                                    latest_version=values[2])

        return 0

    def _pip_download_file(self, package_name: str, current_version: str, latest_version: str) -> None:
        """
        Download the file given by the url and write it to the local_filename.

        # update virtualenv from 15.1.0 to 20.13.0
        pip -q download --no-deps -i https://pypi.org/simple -d /Users/royw/projects/pypiserver/packages \
        virtualenv==20.13.0

        """
        logging.info(f"# update {package_name} from {current_version} to {latest_version}")
        command_line = f"pip -q download --no-deps -i {self.settings.pypi_simple_url} " + \
                       f"-d {self.settings.packages_dir} {package_name}=={latest_version}"
        logging.info(command_line)
        if self.settings.execute_pip_downloads:
            logging.info(subprocess.run(shlex.split(command_line), stdout=subprocess.PIPE).stdout.decode('utf-8'))
