#!/usr/bin/env python3

from datetime import datetime, timezone
from typing import Any, List, Dict, Tuple
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

import yaml


class DetectVersions:

    def __init__(
        self,
        package_name: str,
        constraints_path: str = 'constraints.yml',
        output_path: str = 'dist/versions.yml',
        version_filter: str | None = None,
        scope: str | None = None
    ):

        self.package_name: str = package_name.strip().lower()
        self.constraints_path: str = constraints_path
        self.output_path: str = output_path
        self.version_filter: str | None = version_filter
        self.scope: str | None = scope

        try:
            self.constraints: Dict[str, Any] = self._load_yaml(constraints_path)
        except FileNotFoundError:
            print(f"Warning: Constraints file '{constraints_path}' not found.", file=sys.stderr)
            self.constraints = {}

        self._detectors = {
            'python': self._detect_docker_image,
            'node': self._detect_node_versions,
            'poetry': self._detect_pip_package,
            'uv': self._detect_pip_package,
            'nvm': self._detect_github_repo,
        }

        if self.package_name not in self._detectors:
            raise ValueError(f"Invalid package name '{self.package_name}'.")

        self.detected_versions: List[str] = []
        self.latest_version: str | None = None

    def _load_yaml(self, path: str) -> dict:
        """Load YAML configuration file."""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError as err:
            raise FileNotFoundError(f"Error: {path} not found") from err

    def load_past_detected_versions(self) -> dict:
        """Load cached detected versions from output file."""
        try:
            with open(self.output_path, 'r') as f:
                data = yaml.safe_load(f) or {}
                return data.get('detected_versions', {})
        except Exception:
            return {}

    def _fetch_json(self, url: str, timeout: int = 10) -> dict:
        """Fetch JSON from URL with error handling."""
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'python-devbox/1.0')
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode())
        except (urllib.error.URLError, json.JSONDecodeError) as e:
            print(f"Warning: Failed to fetch {url}: {e}", file=sys.stderr)
            return {}

    def _get_version_tuple(self, version: str) -> Tuple[int, int, int]:
        parts = version.split('.', 2)
        return (
            int(parts[0]),
            int(parts[1]) if len(parts) > 1 else 0,
            int(parts[2]) if len(parts) > 2 else 0
        )

    def _get_version_filter_tuple(self, version_filter: str | None) -> Tuple[int, ...] | None:
        if not version_filter:
            return None
        try:
            return tuple(int(part) for part in version_filter.strip().split('.')[:3])
        except ValueError:
            print(f"Warning: Invalid version filter '{version_filter}', ignoring.", file=sys.stderr)
            return None

    def _version_matches_filter(self, version_tuple: Tuple[int, int, int], filter_tuple: Tuple[int, ...] | None) -> bool:
        if not filter_tuple:
            return True
        return version_tuple[:len(filter_tuple)] == filter_tuple

    def _sort_versions(self, minor_versions: Dict[str, str]) -> List[str]:
        """Sort and return detected versions in descending order."""
        detected_versions = list(minor_versions.values())
        detected_versions.sort(key=lambda v: self._get_version_tuple(v), reverse=True)
        return detected_versions

    def detect_versions(
        self,
        past_detected_versions: List[str] = [],
    ) -> List[str]:
        """Detect package versions using the appropriate detector."""
        print(f"Detecting '{self.package_name}' versions...")

        if self.package_name not in self._detectors:
            raise ValueError(f"No detector available for package '{self.package_name}'.")

        detector = self._detectors[self.package_name]
        self.detected_versions = detector(past_detected_versions)
        print(f"Detected '{self.package_name}' versions: {self.detected_versions}")

        if self.detected_versions and not self.version_filter:
            self.latest_version = self.detected_versions[0]
            print(f"Latest '{self.package_name}' version: {self.latest_version}")

        return self.detected_versions

    def _detect_docker_image(
        self,
        past_detected_versions: List[str] = [],
    ) -> List[str]:
        """Detect package versions from Docker Hub image tags."""

        constraints_incomplete = False

        package_constraints = self.constraints.get(self.package_name, {})
        if not package_constraints:
            print(
                f"Warning: Package '{self.package_name}' not found in constraints; detecting latest version only",
                file=sys.stderr,
            )
            constraints_incomplete = True
        elif not package_constraints.get('min_version'):
            print(
                f"Warning: 'min_version' not specified for '{self.package_name}' in constraints; detecting latest version only",
                file=sys.stderr,
            )
            constraints_incomplete = True

        min_version = package_constraints.get('min_version', '0.0.0')
        min_version_tuple = self._get_version_tuple(min_version)
        extra_versions = set(package_constraints.get('extra_versions', []))
        skip_versions = package_constraints.get('skip_versions', [])
        version_filter_tuple = self._get_version_filter_tuple(self.version_filter)
        minor_versions = {}

        docker_image = package_constraints.get('docker_image')
        if not docker_image:
            known_repos = {
                'python': 'library/python',
            }
            docker_image = known_repos.get(self.package_name)
            if not docker_image:
                print(f"Warning: No 'docker_image' specified in constraints for {self.package_name}", file=sys.stderr)
                return past_detected_versions

        docker_parts = docker_image.split('/')
        url = f"https://hub.docker.com/v2/namespaces/{docker_parts[0]}/repositories/{docker_parts[1]}/tags?page_size=100"

        while True:
            data = self._fetch_json(url)
            if not data:
                print(
                    'Warning: Could not fetch package versions from Docker Hub, using previously cached versions',
                    file=sys.stderr,
                )
            if 'results' not in data:
                break
            found_version = False
            for tag in data['results']:
                try:
                    tag_name = tag.get('name', '')
                    if not tag_name or not re.match(r'^\d+(\.\d+)*$', tag_name):
                        continue
                    version_tuple = self._get_version_tuple(tag_name)
                    version_major = f"{version_tuple[0]}"
                    version_minor = f"{version_tuple[0]}.{version_tuple[1]}"
                    version_full = f"{version_tuple[0]}.{version_tuple[1]}.{version_tuple[2]}"
                    if version_filter_tuple:
                        if not self._version_matches_filter(version_tuple, version_filter_tuple):
                            continue
                        if version_major in skip_versions or version_minor in skip_versions or version_full in skip_versions:
                            continue
                    if ((
                        version_tuple < min_version_tuple and
                        version_major not in extra_versions and version_minor not in extra_versions and version_full not in extra_versions
                    ) or version_major in skip_versions or version_minor in skip_versions or version_full in skip_versions):
                        continue
                    found_version = True
                    if version_minor in minor_versions:
                        existing_full = minor_versions[version_minor]
                        existing_tuple = self._get_version_tuple(existing_full)
                        if version_tuple > existing_tuple:
                            minor_versions[version_minor] = version_full
                    else:
                        minor_versions[version_minor] = version_full
                    # Stop after first version found if constraints are incomplete
                    if constraints_incomplete:
                        break
                except (ValueError, IndexError):
                    pass
            # Break if no versions were found on this page
            # Stop after first page if constraints are incomplete
            if not found_version or constraints_incomplete:
                break
            if 'next' in data and data['next']:
                url = data['next']

        # Fallback to past detected versions if no versions were found
        if not minor_versions and past_detected_versions:
            for version_full in past_detected_versions:
                version_tuple = self._get_version_tuple(version_full)
                version_minor = f"{version_tuple[0]}.{version_tuple[1]}"
                if version_filter_tuple:
                    if not self._version_matches_filter(version_tuple, version_filter_tuple):
                        continue
                if version_tuple < min_version_tuple:
                    continue
                minor_versions[version_minor] = version_full

        return self._sort_versions(minor_versions)

    def _detect_node_versions(
        self,
        past_detected_versions: List[str] = [],
    ) -> List[str]:
        """Detect Node.js versions from Node.js API."""

        constraints_incomplete = False

        package_constraints = self.constraints.get(self.package_name, {})
        if not package_constraints:
            print(
                f"Warning: Package '{self.package_name}' not found in constraints; detecting latest version only",
                file=sys.stderr,
            )
            constraints_incomplete = True
        elif not package_constraints.get('min_version'):
            print(
                f"Warning: 'min_version' not specified for '{self.package_name}' in constraints; detecting latest version only",
                file=sys.stderr,
            )
            constraints_incomplete = True

        min_version = package_constraints.get('min_version', '0.0.0')
        min_version_tuple = self._get_version_tuple(min_version)
        extra_versions = set(package_constraints.get('extra_versions', []))
        skip_versions = package_constraints.get('skip_versions', [])
        version_filter_tuple = self._get_version_filter_tuple(self.version_filter)
        minor_versions = {}

        url = 'https://nodejs.org/dist/index.json'
        data = self._fetch_json(url)

        if not data or not isinstance(data, list):
            print(
                'Warning: Could not fetch versions from Node.js API, using previously cached versions',
                file=sys.stderr,
            )
            return []

        for tag in data:
            try:
                version = tag.get('version', '').lstrip('v')
                if not version or not re.match(r'^\d+(\.\d+)*$', version):
                    continue
                version_tuple = self._get_version_tuple(version)
                version_major = f"{version_tuple[0]}"
                version_minor = f"{version_tuple[0]}.{version_tuple[1]}"
                version_full = f"{version_tuple[0]}.{version_tuple[1]}.{version_tuple[2]}"
                if version_filter_tuple:
                    if not self._version_matches_filter(version_tuple, version_filter_tuple):
                        continue
                    if version_major in skip_versions or version_minor in skip_versions or version_full in skip_versions:
                        continue
                if ((
                    version_tuple < min_version_tuple and
                    version_major not in extra_versions and version_minor not in extra_versions and version_full not in extra_versions
                ) or version_major in skip_versions or version_minor in skip_versions or version_full in skip_versions):
                    continue
                if version_minor in minor_versions:
                    existing_full = minor_versions[version_minor]
                    existing_tuple = self._get_version_tuple(existing_full)
                    if version_tuple > existing_tuple:
                        minor_versions[version_minor] = version_full
                else:
                    minor_versions[version_minor] = version_full
                # Stop after first version found if constraints are incomplete
                if constraints_incomplete:
                    break
            except (ValueError, IndexError):
                pass

        # Fallback to past detected versions if no versions were found
        if not minor_versions and past_detected_versions:
            for version_full in past_detected_versions:
                version_tuple = self._get_version_tuple(version_full)
                version_minor = f"{version_tuple[0]}.{version_tuple[1]}"
                if version_filter_tuple:
                    if not self._version_matches_filter(version_tuple, version_filter_tuple):
                        continue
                if version_tuple < min_version_tuple:
                    continue
                minor_versions[version_minor] = version_full

        return self._sort_versions(minor_versions)

    def _detect_pip_package(
        self,
        past_detected_versions: List[str] = [],
    ) -> List[str]:
        """Detect package versions from PyPI using pip."""

        constraints_incomplete = False

        package_constraints = self.constraints.get(self.package_name, {})
        if not package_constraints:
            print(
                f"Warning: Package '{self.package_name}' not found in constraints; detecting latest version only",
                file=sys.stderr,
            )
            constraints_incomplete = True
        elif not package_constraints.get('min_version'):
            print(
                f"Warning: 'min_version' not specified for '{self.package_name}' in constraints; detecting latest version only",
                file=sys.stderr,
            )
            constraints_incomplete = True

        min_version = package_constraints.get('min_version', '0.0.0')
        min_version_tuple = self._get_version_tuple(min_version)
        extra_versions = set(package_constraints.get('extra_versions', []))
        skip_versions = package_constraints.get('skip_versions', [])
        version_filter_tuple = self._get_version_filter_tuple(self.version_filter)
        minor_versions = {}

        try:
            pip_result = subprocess.run(
                ['pip', 'index', 'versions', self.package_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception as e:
            print(f"Warning: pip index versions failed: {e}", file=sys.stderr)
            pip_result = None

        if pip_result and pip_result.returncode == 0:
            pip_output = pip_result.stdout
            if 'Available versions:' in pip_output:
                version_list = [
                    v.strip()
                    for v in pip_output.split('Available versions:')[1].strip().split(',')
                ]
                for version in version_list:
                    try:
                        if not version or not re.match(r'^\d+(\.\d+)*$', version):
                            continue
                        version_tuple = self._get_version_tuple(version)
                        version_major = f"{version_tuple[0]}"
                        version_minor = f"{version_tuple[0]}.{version_tuple[1]}"
                        version_full = f"{version_tuple[0]}.{version_tuple[1]}.{version_tuple[2]}"
                        if version_filter_tuple:
                            if not self._version_matches_filter(version_tuple, version_filter_tuple):
                                continue
                            if version_major in skip_versions or version_minor in skip_versions or version_full in skip_versions:
                                continue
                        if ((
                            version_tuple < min_version_tuple and
                            version_major not in extra_versions and version_minor not in extra_versions and version_full not in extra_versions
                        ) or version_major in skip_versions or version_minor in skip_versions or version_full in skip_versions):
                            continue
                        if version_minor in minor_versions:
                            existing_full = minor_versions[version_minor]
                            existing_tuple = self._get_version_tuple(existing_full)
                            if version_tuple > existing_tuple:
                                minor_versions[version_minor] = version_full
                        else:
                            minor_versions[version_minor] = version_full
                        # Stop after first version found if constraints are incomplete
                        if constraints_incomplete:
                            break
                    except (ValueError, IndexError):
                        pass

        # Fallback to past detected versions if no versions were found
        if not minor_versions and past_detected_versions:
            for version_full in past_detected_versions:
                version_tuple = self._get_version_tuple(version_full)
                version_minor = f"{version_tuple[0]}.{version_tuple[1]}"
                if version_filter_tuple:
                    if not self._version_matches_filter(version_tuple, version_filter_tuple):
                        continue
                if version_tuple < min_version_tuple:
                    continue
                minor_versions[version_minor] = version_full

        return self._sort_versions(minor_versions)

    def _detect_github_repo(
        self,
        past_detected_versions: List[str] = [],
    ) -> List[str]:
        """Detect package versions from GitHub repository tags."""

        constraints_incomplete = False

        package_constraints = self.constraints.get(self.package_name, {})
        if not package_constraints:
            print(
                f"Warning: Package '{self.package_name}' not found in constraints; detecting latest version only",
                file=sys.stderr,
            )
            constraints_incomplete = True
        elif not package_constraints.get('min_version'):
            print(
                f"Warning: 'min_version' not specified for '{self.package_name}' in constraints; detecting latest version only",
                file=sys.stderr,
            )
            constraints_incomplete = True

        min_version = package_constraints.get('min_version', '0.0.0')
        min_version_tuple = self._get_version_tuple(min_version)
        extra_versions = set(package_constraints.get('extra_versions', []))
        skip_versions = package_constraints.get('skip_versions', [])
        version_filter_tuple = self._get_version_filter_tuple(self.version_filter)
        minor_versions = {}

        github_repo = package_constraints.get('github_repo')
        if not github_repo:
            known_repos = {
                'nvm': 'nvm-sh/nvm',
            }
            github_repo = known_repos.get(self.package_name)
            if not github_repo:
                print(f"Warning: No 'github_repo' specified in constraints for {self.package_name}", file=sys.stderr)
                return past_detected_versions

        url = f'https://api.github.com/repos/{github_repo}/tags'
        page = 1

        while True:
            page_url = f"{url}?per_page=100&page={page}"
            data = self._fetch_json(page_url)

            if not data or not isinstance(data, list):
                if page == 1:
                    print(
                        f'Warning: Could not fetch tags from GitHub for {self.package_name}, using previously cached versions',
                        file=sys.stderr,
                    )
                break

            found_version = False
            for tag in data:
                try:
                    tag_name = tag.get('name', '').lstrip('v')
                    if not tag_name or not re.match(r'^\d+(\.\d+)*$', tag_name):
                        continue
                    version_tuple = self._get_version_tuple(tag_name)
                    version_major = f"{version_tuple[0]}"
                    version_minor = f"{version_tuple[0]}.{version_tuple[1]}"
                    version_full = f"{version_tuple[0]}.{version_tuple[1]}.{version_tuple[2]}"
                    if version_filter_tuple:
                        if not self._version_matches_filter(version_tuple, version_filter_tuple):
                            continue
                        if version_major in skip_versions or version_minor in skip_versions or version_full in skip_versions:
                            continue
                    if ((
                        version_tuple < min_version_tuple and
                        version_major not in extra_versions and version_minor not in extra_versions and version_full not in extra_versions
                    ) or version_major in skip_versions or version_minor in skip_versions or version_full in skip_versions):
                        continue
                    found_version = True
                    if version_minor in minor_versions:
                        existing_full = minor_versions[version_minor]
                        existing_tuple = self._get_version_tuple(existing_full)
                        if version_tuple > existing_tuple:
                            minor_versions[version_minor] = version_full
                    else:
                        minor_versions[version_minor] = version_full
                    # Stop after first version found if constraints are incomplete
                    if constraints_incomplete:
                        break
                except (ValueError, IndexError):
                    pass
            # Break if no versions were found on this page
            # Stop after first page if constraints are incomplete
            if not found_version or constraints_incomplete:
                break
            page += 1

        # Fallback to past detected versions if no versions were found
        if not minor_versions and past_detected_versions:
            for version_full in past_detected_versions:
                version_tuple = self._get_version_tuple(version_full)
                version_minor = f"{version_tuple[0]}.{version_tuple[1]}"
                if version_filter_tuple:
                    if not self._version_matches_filter(version_tuple, version_filter_tuple):
                        continue
                if version_tuple < min_version_tuple:
                    continue
                minor_versions[version_minor] = version_full

        return self._sort_versions(minor_versions)

    def save_versions_file(self):
        """Save detected versions to output file."""
        print(f"Saving '{self.package_name}' versions to {self.output_path}...")

        # Load existing data to preserve past detected versions
        try:
            with open(self.output_path, 'r') as f:
                existing = yaml.safe_load(f) or {}
        except FileNotFoundError:
            existing = {}

        data = {
            **existing,
            'last_updated': datetime.now(timezone.utc).isoformat() + 'Z',
            'detected_versions': {
                **(existing.get('detected_versions') or {}),
                self.package_name: self.detected_versions,
            },
            'latest_version': {
                **(existing.get('latest_version') or {}),
                **({ self.package_name: self.latest_version } if self.latest_version else {}),
            }
        }

        # Save to output file
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        with open(self.output_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        print(f"Versions saved to {self.output_path}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Detect package versions.',
    )
    parser.add_argument(
        'package_name',
        help=(
            'Package name (\'python\', \'poetry\', \'uv\', or \'nvm\'). '
            'Can also be specified via --package option.'
        ),
    )
    parser.add_argument(
        '--package',
        dest='package_option',
        default='',
        help='Alternative way to specify package name (positional argument takes precedence)',
    )
    parser.add_argument(
        '--version',
        default='',
        help=(
            'Limit detection to a specific version (e.g., \'3\', \'3.14\', or \'3.13.14\'). '
            'Detects all versions if left empty.'
        ),
    )
    parser.add_argument(
        '--scope',
        help=(
            'Restrict detection to a specific scope (e.g., \'major\', \'minor\', or \'full\'). '
            'Defaults depending on the package type: for example, Python defaults to \'minor\', while Node.js defaults to \'major\'.'
        ),
    )
    return parser.parse_args()


def main():

    args = parse_args()

    package_name = args.package_name or args.package_option
    if not package_name:
        print('Error: Package name is required. Provide it as a positional argument or via --package option.', file=sys.stderr)
        sys.exit(1)

    try:
        detector = DetectVersions(
            package_name=package_name,
            version_filter=(args.version.strip() or None),
            scope=(args.scope.strip() or None)
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Load past detected versions to use as fallback
    past_detected_versions = detector.load_past_detected_versions()

    # Detect versions
    detector.detect_versions(
        past_detected_versions=past_detected_versions.get(detector.package_name, []),
    )

    # Save versions file
    detector.save_versions_file()


if __name__ == "__main__":
    main()
