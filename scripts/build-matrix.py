#!/usr/bin/env python3

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
import argparse
import itertools
import json
import os
import re
import sys
import urllib.error
import urllib.request

import yaml


class BuildMatrix:

    def __init__(
        self,
        packages: List[str],
        versions_path: str = 'dist/versions.yml',
        constraints_path: str = 'constraints.yml',
        output_path: str = 'dist/build-matrix.yml',
    ):
        self.packages: List[str] = [ package.strip().lower() for package in packages ] if packages else []
        self.versions: Dict[str, Any] = self._load_yaml(versions_path)
        self.constraints: Dict[str, Any] = self._load_yaml(constraints_path)
        self.output_path: str = output_path
        self.build_matrix: List[Dict[str, str]] = []

        if not self.packages:
            raise ValueError('No packages specified for build matrix generation.')

    def _load_yaml(self, path: str) -> dict:
        """Load YAML configuration file."""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"Error: {path} not found", file=sys.stderr)
            sys.exit(1)

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
                    published_tags.append(tag_name)
                except (ValueError, IndexError):
                    pass
            url = data.get('next')

        return published_tags

    def generate_build_matrix(
        self,
        skip_published_tags: bool = True,
    ) -> List[dict[str, str]]:
        """Generate build matrix from detected versions for specified packages."""
        print(f'Generating build matrix for packages: {", ".join(self.packages)}...')

        all_detected_versions = self.versions.get('detected_versions', {})
        all_latest_versions = self.versions.get('latest_version', {})
        all_base_variants = {
            'python': ['', 'slim', 'alpine'],
        }

        base_package = self.packages[0]
        other_packages = self.packages[1:]

        detected_versions = {}
        latest_versions = {}
        for package in self.packages:
            package_versions = all_detected_versions.get(package, [])
            if not package_versions:
                print(f"Error: No detected versions found for package '{package}'.", file=sys.stderr)
                sys.exit(1)
            detected_versions[package] = package_versions
            latest_versions[package] = all_latest_versions.get(package, package_versions[0])

        base_variants = all_base_variants.get(base_package) or [None]

        if skip_published_tags:
            published_tags = set(self._fetch_published_tags())
            print(f"Detected {len(published_tags)} published tags.")
        else:
            published_tags = set()
            print('Skipped published tags check.')

        build_matrix = []

        for versions_combo in itertools.product(*detected_versions.values()):
            packages_version = dict(zip(self.packages, versions_combo))

            for variant in base_variants:

                tag_parts = [packages_version[base_package]]
                if variant:
                    tag_parts.append(variant)
                for package in other_packages:
                    tag_parts.append(f"{package}{packages_version[package]}")
                image_tag = '-'.join(tag_parts)

                if image_tag not in published_tags:
                    entry = {
                        'image_tag': image_tag,
                        f"{base_package}_version": packages_version[base_package],
                        f"{base_package}_tag_level": 'global' if packages_version[base_package] == latest_versions[base_package] else 'minor',
                    }
                    if variant is not None:
                        entry[f"{base_package}_image_variant"] = variant

                    for package in other_packages:
                        entry[f'{package}_version'] = packages_version[package]
                        entry[f'{package}_tag_level'] = 'global' if packages_version[package] == latest_versions[package] else 'minor'

                    build_matrix.append(entry)

        print(f"Generated {len(build_matrix)} build matrix entries.")
        self.build_matrix = build_matrix
        return build_matrix

    def save_build_matrix_file(self, append: bool = False) -> None:
        """Save build matrix to output file."""
        print(f"Saving build matrix to {self.output_path}...")

        # Load existing data to preserve past detected versions
        try:
            with open(self.output_path, 'r') as f:
                existing = yaml.safe_load(f) or {}
        except FileNotFoundError:
            existing = {}

        if append:
            build_matrix = existing.get('build_matrix', []) + self.build_matrix
        else:
            build_matrix = self.build_matrix

        data = {
            'last_updated': datetime.now(timezone.utc).isoformat() + 'Z',
            'build_matrix': build_matrix,
        }

        # Save to output file
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        with open(self.output_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        print(f"Build matrix saved to {self.output_path}.")


def _parse_bool(value: str) -> bool:
    """Parse string to boolean."""
    if isinstance(value, bool):
        return value
    return value.lower() in ('true', '1', 'yes', 'on')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Generate build matrix from detected versions.',
    )
    parser.add_argument(
        'packages',
        nargs='*',
        default=[],
        help='Packages to include in build matrix. If empty, all are included.',
    )
    parser.add_argument(
        '--append',
        action='store_true',
        default=False,
        help=(
            'Append to existing build matrix instead of overwriting. '
            'This will merge new entries with existing ones.'
        ),
    )
    parser.add_argument(
        '--skip-published-tags',
        type=_parse_bool,
        default=True,
        help=(
            'Skip tags already published to the registry (true/false). '
            'Set to false to force rebuild/inclusion of existing tags.'
        ),
    )
    return parser.parse_args()


def main():

    args = parse_args()

    try:
        matrix_builder = BuildMatrix(
            packages=args.packages,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate build matrix
    matrix_builder.generate_build_matrix(
        skip_published_tags=args.skip_published_tags,
    )

    # Save build matrix file
    matrix_builder.save_build_matrix_file(
        append=args.append,
    )


if __name__ == "__main__":
    main()
