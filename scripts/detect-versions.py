#!/usr/bin/env python3

from datetime import datetime, timezone
from typing import Any, List, Dict
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
        constraints_path: str = 'constraints.yml',
        output_path: str = 'dist/versions.yml',
    ):
        self.constraints: Dict[str, Any] = self._load_yaml(constraints_path)
        self.output_path: str = output_path
        self.python_versions: List[str] = []
        self.poetry_versions: List[str] = []
        self.uv_versions: List[str] = []
        self.published_versions: Dict[str, List[str]] = {}
        self.build_matrix: List[Dict[str, str]] = []

    def _load_yaml(self, path: str) -> dict:
        """Load YAML configuration file."""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Error: {path} not found", file=sys.stderr)
            sys.exit(1)

    def load_past_detected_versions(self) -> dict:
        """Load cached detected versions from output file."""
        try:
            with open(self.output_path, 'r') as f:
                data = yaml.safe_load(f) or {}
                return data.get('detected_versions', {})
        except Exception as e:
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

    def _get_version_tuple(self, version: str) -> tuple:
        parts = version.split('.', 2)
        return (
            int(parts[0]),
            int(parts[1]) if len(parts) > 1 else 0,
            int(parts[2]) if len(parts) > 2 else 0
        )

    def detect_python_versions(
        self,
        past_detected_versions: List[str] = [],
    ) -> List[str]:
        """Detect latest Python versions and image tags from Docker Hub."""
        print('Detecting Python versions...')

        min_version = self.constraints['python']['min_version']
        min_version_tuple = self._get_version_tuple(min_version)
        extra_versions = set(self.constraints['python'].get('extra_versions', []))
        skip_versions = self.constraints['python'].get('skip_tags', [])
        minor_versions = {}

        url = 'https://hub.docker.com/v2/namespaces/library/repositories/python/tags?page_size=100'
        while True:
            data = self._fetch_json(url)
            if not data:
                print(
                    'Warning: Could not fetch Python versions from Docker Hub, using previously cached versions',
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
                    version_minor = f"{version_tuple[0]}.{version_tuple[1]}"
                    version_full = f"{version_tuple[0]}.{version_tuple[1]}.{version_tuple[2]}"
                    if ((
                        version_tuple < min_version_tuple and
                        version_minor not in extra_versions and version_full not in extra_versions
                    ) or version_minor in skip_versions or version_full in skip_versions):
                        continue
                    found_version = True
                    if version_minor in minor_versions:
                        existing_full = minor_versions[version_minor]
                        existing_tuple = self._get_version_tuple(existing_full)
                        if version_tuple > existing_tuple:
                            minor_versions[version_minor] = version_full
                    else:
                        minor_versions[version_minor] = version_full
                except (ValueError, IndexError):
                    pass
            if not found_version:
                break
            if 'next' in data and data['next']:
                url = data['next']

        # Fallback to past detected versions if no versions were found
        if not minor_versions and past_detected_versions:
            for version_full in past_detected_versions:
                version_tuple = self._get_version_tuple(version_full)
                version_minor = f"{version_tuple[0]}.{version_tuple[1]}"
                if version_tuple >= min_version_tuple:
                    minor_versions[version_minor] = version_full

        detected_versions = list(minor_versions.values())
        detected_versions.sort(key=lambda v: self._get_version_tuple(v), reverse=True)
        print(f"Detected Python versions: {detected_versions}")
        self.python_versions = detected_versions
        return detected_versions

    def _detect_pip_package_versions(
        self,
        package_name: str,
        min_version: str,
        extra_versions: List[str] = [],
        skip_versions: List[str] = [],
        past_detected_versions: List[str] = [],
    ) -> List[str]:
        """Detect package versions from PyPI using pip."""

        min_version_tuple = self._get_version_tuple(min_version)
        minor_versions = {}

        try:
            pip_result = subprocess.run(
                ['pip', 'index', 'versions', package_name],
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
                        version_minor = f"{version_tuple[0]}.{version_tuple[1]}"
                        version_full = f"{version_tuple[0]}.{version_tuple[1]}.{version_tuple[2]}"
                        if ((
                            version_tuple < min_version_tuple and
                            version_minor not in extra_versions and version_full not in extra_versions
                        ) or version_minor in skip_versions or version_full in skip_versions):
                            continue
                        if version_minor in minor_versions:
                            existing_full = minor_versions[version_minor]
                            existing_tuple = self._get_version_tuple(existing_full)
                            if version_tuple > existing_tuple:
                                minor_versions[version_minor] = version_full
                        else:
                            minor_versions[version_minor] = version_full
                    except (ValueError, IndexError):
                        pass

        # Fallback to past detected versions if no versions were found
        if not minor_versions and past_detected_versions:
            for version_full in past_detected_versions:
                version_tuple = self._get_version_tuple(version_full)
                version_minor = f"{version_tuple[0]}.{version_tuple[1]}"
                if version_tuple >= min_version_tuple:
                    minor_versions[version_minor] = version_full

        detected_versions = list(minor_versions.values())
        detected_versions.sort(key=lambda v: self._get_version_tuple(v), reverse=True)
        return detected_versions

    def detect_poetry_versions(
        self,
        past_detected_versions: List[str] = [],
    ) -> List[str]:
        """Detect Poetry versions from PyPI using pip."""
        print('Detecting Poetry versions...')
        detected_versions = self._detect_pip_package_versions(
            package_name='poetry',
            min_version=self.constraints['poetry']['min_version'],
            extra_versions=self.constraints['poetry'].get('extra_versions', []),
            skip_versions=self.constraints['poetry'].get('skip_tags', []),
            past_detected_versions=past_detected_versions,
        )
        print(f"Detected Poetry versions: {detected_versions}")
        self.poetry_versions = detected_versions
        return detected_versions

    def detect_uv_versions(
        self,
        past_detected_versions: List[str] = [],
    ) -> List[str]:
        """Detect uv versions using pip."""
        print('Detecting uv versions...')
        detected_versions = self._detect_pip_package_versions(
            package_name='uv',
            min_version=self.constraints['uv']['min_version'],
            extra_versions=self.constraints['uv'].get('extra_versions', []),
            skip_versions=self.constraints['uv'].get('skip_tags', []),
            past_detected_versions=past_detected_versions,
        )
        print(f"Detected uv versions: {detected_versions}")
        self.uv_versions = detected_versions
        return detected_versions

    def _fetch_published_tags(self) -> List[str]:
        """Fetch published tags from Docker Hub."""

        published_tags: List[str] = []

        min_python_version = self.constraints['python']['min_version']
        min_poetry_version = self.constraints['poetry']['min_version']
        min_uv_version = self.constraints['uv']['min_version']
        min_python_version_tuple = self._get_version_tuple(min_python_version)
        min_poetry_version_tuple = self._get_version_tuple(min_poetry_version)
        min_uv_version_tuple = self._get_version_tuple(min_uv_version)

        url: str | None = 'https://hub.docker.com/v2/namespaces/matiboux/repositories/python-devbox/tags?page_size=100'
        for _ in range(100):  # Limit to 100 pages to avoid infinite loop
            if not url:
                break
            data = self._fetch_json(url)
            if not data:
                print(
                    'Warning: Could not fetch published tags from Docker Hub',
                    file=sys.stderr,
                )
            if 'results' not in data:
                break
            for tag in data['results']:
                try:
                    tag_name = tag.get('name', '')
                    if not tag_name or 'slim' in tag_name:
                        continue
                    tag_match = re.match(r'^(?P<python>\d+\.\d+\.\d+)(?:-poetry(?P<poetry>\d+\.\d+\.\d+))?(?:-uv(?P<uv>\d+\.\d+\.\d+))?$', tag_name)
                    if not tag_match:
                        continue
                    python_version = tag_match.group('python')
                    poetry_version = tag_match.group('poetry')
                    uv_version = tag_match.group('uv')
                    if python_version:
                        python_version_tuple = self._get_version_tuple(python_version)
                        if python_version_tuple < min_python_version_tuple:
                            continue
                    if poetry_version:
                        poetry_version_tuple = self._get_version_tuple(poetry_version)
                        if poetry_version_tuple < min_poetry_version_tuple:
                            continue
                    if uv_version:
                        uv_version_tuple = self._get_version_tuple(uv_version)
                        if uv_version_tuple < min_uv_version_tuple:
                            continue
                    found_version = True
                    published_tags.append(tag_name)
                except (ValueError, IndexError):
                    pass
            url = data.get('next')

        return published_tags

    def generate_build_matrix(
        self,
        skip_published_tags: bool = True,
    ) -> List[dict[str, str]]:
        """Generate GitHub Actions matrix from detected versions."""
        print('Generating build matrix...')

        if skip_published_tags:
            published_tags = set(self._fetch_published_tags())
            print(f"Detected {len(published_tags)} published tags.")
        else:
            published_tags = set()
            print('Skipped published tags check.')

    #   python_version:
    #   python_image_variant:
    #   poetry_version:
    #   uv_version:
    #   python_tag_level:
    #   poetry_tag_level:
    #   uv_tag_level:

        latest_python_version = self.python_versions[0] if self.python_versions else None
        latest_poetry_version = self.poetry_versions[0] if self.poetry_versions else None
        latest_uv_version = self.uv_versions[0] if self.uv_versions else None

        build_matrix = []
        for python_version in self.python_versions:
            python_tag_level = 'global' if python_version == latest_python_version else 'minor'
            if f"{python_version}" not in published_tags:
                build_matrix.append({
                    'image_tag': f"{python_version}",
                    'python_version': python_version,
                    'python_image_variant': '',
                    'python_tag_level': python_tag_level,
                })
                build_matrix.append({
                    'image_tag': f"{python_version}-slim",
                    'python_version': python_version,
                    'python_image_variant': 'slim',
                    'python_tag_level': python_tag_level,
                })
                build_matrix.append({
                    'image_tag': f"{python_version}-alpine",
                    'python_version': python_version,
                    'python_image_variant': 'alpine',
                    'python_tag_level': python_tag_level,
                })
            for poetry_version in self.poetry_versions:
                poetry_tag_level = 'global' if poetry_version == latest_poetry_version else 'minor'
                if f"{python_version}-poetry{poetry_version}" not in published_tags:
                    build_matrix.append({
                        'image_tag': f"{python_version}-poetry{poetry_version}",
                        'python_version': python_version,
                        'python_image_variant': '',
                        'poetry_version': poetry_version,
                        'python_tag_level': python_tag_level,
                        'poetry_tag_level': poetry_tag_level,
                    })
                    build_matrix.append({
                        'image_tag': f"{python_version}-slim-poetry{poetry_version}",
                        'python_version': python_version,
                        'python_image_variant': 'slim',
                        'poetry_version': poetry_version,
                        'python_tag_level': python_tag_level,
                        'poetry_tag_level': poetry_tag_level,
                    })
                    build_matrix.append({
                        'image_tag': f"{python_version}-alpine-poetry{poetry_version}",
                        'python_version': python_version,
                        'python_image_variant': 'alpine',
                        'poetry_version': poetry_version,
                        'python_tag_level': python_tag_level,
                        'poetry_tag_level': poetry_tag_level,
                    })
            for uv_version in self.uv_versions:
                uv_tag_level = 'global' if uv_version == latest_uv_version else 'minor'
                if f"{python_version}-uv{uv_version}" not in published_tags:
                    build_matrix.append({
                        'image_tag': f"{python_version}-uv{uv_version}",
                        'python_version': python_version,
                        'python_image_variant': '',
                        'uv_version': uv_version,
                        'python_tag_level': python_tag_level,
                        'uv_tag_level': uv_tag_level,
                    })
                    build_matrix.append({
                        'image_tag': f"{python_version}-slim-uv{uv_version}",
                        'python_version': python_version,
                        'python_image_variant': 'slim',
                        'uv_version': uv_version,
                        'python_tag_level': python_tag_level,
                        'uv_tag_level': uv_tag_level,
                    })
                    build_matrix.append({
                        'image_tag': f"{python_version}-alpine-uv{uv_version}",
                        'python_version': python_version,
                        'python_image_variant': 'alpine',
                        'uv_version': uv_version,
                        'python_tag_level': python_tag_level,
                        'uv_tag_level': uv_tag_level,
                    })

        print(f"Generated {len(build_matrix)} build matrix entries.")
        self.build_matrix = build_matrix
        return build_matrix

    def save_versions_file(self):
        """Save detected versions and build matrix to output file."""
        print(f"Saving versions to {self.output_path}...")

        # Load existing data to preserve past detected versions
        try:
            with open(self.output_path, 'r') as f:
                existing = yaml.safe_load(f) or {}
        except FileNotFoundError:
            existing = {}

        python_versions = self.python_versions or existing.get('detected_versions', {}).get('python', {})
        poetry_versions = self.poetry_versions or existing.get('detected_versions', {}).get('poetry', [])
        uv_versions = self.uv_versions or existing.get('detected_versions', {}).get('uv', [])
        build_matrix = self.build_matrix or existing.get('build_matrix', [])

        data = {
            'last_updated': datetime.now(timezone.utc).isoformat() + 'Z',
            'detected_versions': {
                'python': python_versions,
                'poetry': poetry_versions,
                'uv': uv_versions,
            },
            'build_matrix': build_matrix,
        }

        # Save to output file
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        with open(self.output_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        print(f"Versions saved to {self.output_path}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Detect Python Devbox versions and generate the build matrix.',
    )
    parser.add_argument(
        '--check-published-tags',
        default='true',
        help=(
            'Skip tags already published to the registry (true/false). '
            'Set to false to force rebuild/inclusion of existing tags.'
        ),
    )
    return parser.parse_args()


def _str_to_bool(value: str) -> bool:
    return str(value).strip().lower() not in ('false', '0', 'no')


def main():

    args = parse_args()

    detector = DetectVersions()

    # Load past detected versions to use as fallback
    past_detected_versions = detector.load_past_detected_versions()

    # Detect versions
    detector.detect_python_versions(
        past_detected_versions=past_detected_versions.get('python', []),
    )
    detector.detect_poetry_versions(
        past_detected_versions=past_detected_versions.get('poetry', []),
    )
    detector.detect_uv_versions(
        past_detected_versions=past_detected_versions.get('uv', []),
    )

    # Generate build matrix
    detector.generate_build_matrix(
        skip_published_tags=_str_to_bool(args.check_published_tags),
    )

    # Save versions file
    detector.save_versions_file()


if __name__ == "__main__":
    main()
