#!/usr/bin/env python3

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple, Set
import argparse
import itertools
import json
import os
import re
import sys
import urllib.error
import urllib.request

import yaml


class FetchPublishedTags:

    def __init__(
        self,
        image_name: str = 'python-devbox',
        github_read_token: str | None = None,
        ignore_tags_older_than: datetime | None = None,
        output_path: str = 'dist/published_tags.yaml'
    ):
        self.image_name: str = image_name
        self.github_read_token: str | None = github_read_token or os.environ.get('GITHUB_READ_TOKEN') or os.environ.get('GITHUB_TOKEN')
        self.ignore_tags_older_than: datetime = ignore_tags_older_than or (datetime.now(timezone.utc) - timedelta(days=30))
        self.output_path: str = output_path

        if not self.image_name:
            raise ValueError('Empty image name provided. Please specify a valid image name.')

        self.published_tags: Set[str] = set()

    def fetch_published_tags(self) -> Set[str]:
        """Fetch published tags from Docker Hub."""

        if not self.image_name:
            self.published_tags = set()
            return self.published_tags
        if not self.github_read_token:
            print('Warning: GitHub read token not provided, cannot fetch published tags.', file=sys.stderr)
            self.published_tags = set()
            return self.published_tags

        published_tags: Set[str] = set()

        url = f"https://api.github.com/users/matiboux/packages/container/{self.image_name}/versions"
        for page in range(1, 101):  # Limit to 100 pages to avoid too many requests

            page_url = f"{url}?per_page=100&page={page}"
            try:
                req = urllib.request.Request(page_url)
                req.add_header('Authorization', f'token {self.github_read_token}')
                req.add_header('User-Agent', 'python-devbox/1.0')
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
            except (urllib.error.URLError, json.JSONDecodeError):
                print('Warning: Failed to fetch tags from GitHub API.', file=sys.stderr)
                break
            if not data or not isinstance(data, list):
                break

            for package_version in data:
                if not isinstance(package_version, dict):
                    continue
                package_version_tags = package_version.get('metadata', {}).get('container', {}).get('tags', [])
                published_tags.update(package_version_tags)

        self.published_tags = published_tags
        return published_tags

    def save_published_tags_file(self, append: bool = False) -> None:
        """Save published tags to output file."""
        print(f"Saving published tags to {self.output_path}...")

        if append:
            # Load existing data to preserve past detected versions
            try:
                with open(self.output_path, 'r') as f:
                    existing = yaml.safe_load(f) or {}
            except FileNotFoundError:
                existing = {}
            published_tags = list(set(existing.get('published_tags', [])) | self.published_tags)
        else:
            published_tags = list(self.published_tags)

        data = {
            'last_updated': datetime.now(timezone.utc).isoformat() + 'Z',
            'published_tags': published_tags,
        }

        # Save to output file
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        with open(self.output_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        print(f"Published tags saved to {self.output_path}.")


def _parse_ignore_tags_older_than(value: str) -> datetime:
    """Parse ignore-tags-older-than argument to datetime."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Fetch published tags from GitHub.',
    )
    parser.add_argument(
        'image-name',
        nargs='?',
        default='python-devbox',
        help='Package name to fetch published tags for (defaults to \'python-devbox\').',
    )
    parser.add_argument(
        '--github-read-token',
        type=str,
        default=None,
        help=(
            'GitHub token for reading published tags from the GitHub API. '
            'Fall back to the GITHUB_READ_TOKEN or GITHUB_TOKEN environment variables if not provided. '
            'Required to skip published tags.'
        ),
    )
    parser.add_argument(
        '--ignore-tags-older-than',
        type=_parse_ignore_tags_older_than,
        default=None,
        help=(
            'Ignore tags older than the specified date (ISO 8601 format). '
            'Defaults to one month ago if not specified.'
        ),
    )
    parser.add_argument(
        '--append',
        action='store_true',
        default=False,
        help=(
            'Append to existing published tags file instead of overwriting. '
            'This will merge new entries with existing ones.'
        ),
    )
    return parser.parse_args()


def main():

    args = parse_args()

    try:
        fetcher = FetchPublishedTags(
            image_name='python-devbox',
            github_read_token=args.github_read_token,
            ignore_tags_older_than=args.ignore_tags_older_than,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Fetch published tags
    fetcher.fetch_published_tags()

    # Save published tags file
    fetcher.save_published_tags_file(
        append=args.append,
    )


if __name__ == "__main__":
    main()
