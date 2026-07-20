#!/usr/bin/env python3

import argparse
import os
import sys
from itertools import product
from typing import List, Tuple


class ImageTagGenerator:

    def __init__(
        self,
        python_version: str = '3.14.6',
        python_image_variant: str = '',
        poetry_version: str = '',
        uv_version: str = '',
        nvm_version: str = '',
        node_version: str = '',
        python_tag_level: str = 'patch',
        poetry_tag_level: str = 'patch',
        uv_tag_level: str = 'patch',
        nvm_tag_level: str = 'patch',
        node_tag_level: str = 'patch',
        compact_output: bool = False,
    ):
        self.python_version = python_version
        self.python_image_variant = python_image_variant
        self.poetry_version = poetry_version
        self.uv_version = uv_version
        self.nvm_version = nvm_version
        self.node_version = node_version
        self.python_tag_level = self._validate_tag_level(python_tag_level)
        self.poetry_tag_level = self._validate_tag_level(poetry_tag_level)
        self.uv_tag_level = self._validate_tag_level(uv_tag_level)
        self.nvm_tag_level = self._validate_tag_level(nvm_tag_level)
        self.node_tag_level = self._validate_tag_level(node_tag_level)
        self.compact_output = compact_output

        self.image_tags: List[str] = []

    @staticmethod
    def _validate_tag_level(level: str) -> str:
        if level in ('global', 'major', 'minor', 'patch'):
            return level
        return 'patch'

    def _get_component_options(self, version: str, level: str) -> List[str]:
        if not version:
            return []

        version_parts = version.split('.')
        major = version_parts[0]
        minor = f"{version_parts[0]}.{version_parts[1]}" if len(version_parts) >= 2 else version

        raw_options: List[str] = []
        if level == 'global':
            raw_options = [version, minor, major, '']
        elif level == 'major':
            raw_options = [version, minor, major]
        elif level == 'minor':
            raw_options = [version, minor]
        elif level == 'patch':
            raw_options = [version]

        # De-duplicate while preserving order
        options: List[str] = []
        for item in raw_options:
            if item not in options:
                options.append(item)

        return options

    def _get_prefixed_options(self, prefix: str, version: str, tag_level: str) -> List[str]:
        if not version:
            return ['']

        options = self._get_component_options(version, tag_level)
        return [f"{prefix}{opt}" for opt in options]

    def generate_tags(self) -> List[str]:
        python_options = self._get_component_options(self.python_version, self.python_tag_level)
        print(f"Python component options: {python_options}", file=sys.stderr)

        node_options = self._get_prefixed_options('node', self.node_version, self.node_tag_level)
        print(f"Node component options: {node_options}", file=sys.stderr)

        poetry_options = self._get_prefixed_options('poetry', self.poetry_version, self.poetry_tag_level)
        print(f"Poetry component options: {poetry_options}", file=sys.stderr)

        uv_options = self._get_prefixed_options('uv', self.uv_version, self.uv_tag_level)
        print(f"uv component options: {uv_options}", file=sys.stderr)

        nvm_options = self._get_prefixed_options('nvm', self.nvm_version, self.nvm_tag_level)
        print(f"nvm component options: {nvm_options}", file=sys.stderr)

        tags: List[str] = []
        for python_comp, node_comp, poetry_comp, uv_comp, nvm_comp in product(
            python_options, node_options, poetry_options, uv_options, nvm_options
        ):
            tag_pieces: List[str] = []

            if python_comp:
                tag_pieces.append(python_comp)
            if self.python_image_variant:
                tag_pieces.append(self.python_image_variant)
            if node_comp:
                tag_pieces.append(node_comp)
            if poetry_comp:
                tag_pieces.append(poetry_comp)
            if uv_comp:
                tag_pieces.append(uv_comp)
            if nvm_comp:
                tag_pieces.append(nvm_comp)

            if not tag_pieces:
                image_tag = 'latest'
            else:
                image_tag = '-'.join(tag_pieces)

            tags.append(image_tag)

        self.image_tags = tags
        return tags

    def output_tags(self) -> None:
        if self.compact_output:
            print(','.join(self.image_tags))
        else:
            for tag in self.image_tags:
                print(tag)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Generate Docker image tags for the devbox image.',
    )
    parser.add_argument(
        '-c', '--compact',
        action='store_true',
        help='Output tags as comma-separated values on a single line',
    )
    parser.add_argument(
        '--python-version',
        default=os.getenv('PYTHON_VERSION', '3.14.6'),
        help='Python version (default: 3.14.6)',
    )
    parser.add_argument(
        '--python-image-variant',
        default=os.getenv('PYTHON_IMAGE_VARIANT', ''),
        help='Python image variant: empty, slim, or alpine',
    )
    parser.add_argument(
        '--poetry-version',
        default=os.getenv('POETRY_VERSION', ''),
        help='Poetry version',
    )
    parser.add_argument(
        '--uv-version',
        default=os.getenv('UV_VERSION', ''),
        help='UV version',
    )
    parser.add_argument(
        '--nvm-version',
        default=os.getenv('NVM_VERSION', ''),
        help='NVM version',
    )
    parser.add_argument(
        '--node-version',
        default=os.getenv('NODE_VERSION', ''),
        help='Node version',
    )
    parser.add_argument(
        '--python-tag-level',
        default=os.getenv('PYTHON_TAG_LEVEL', 'patch'),
        help='Python tag level: global, major, minor, or patch (default: patch)',
    )
    parser.add_argument(
        '--poetry-tag-level',
        default=os.getenv('POETRY_TAG_LEVEL', 'patch'),
        help='Poetry tag level: global, major, minor, or patch (default: patch)',
    )
    parser.add_argument(
        '--uv-tag-level',
        default=os.getenv('UV_TAG_LEVEL', 'patch'),
        help='UV tag level: global, major, minor, or patch (default: patch)',
    )
    parser.add_argument(
        '--nvm-tag-level',
        default=os.getenv('NVM_TAG_LEVEL', 'patch'),
        help='NVM tag level: global, major, minor, or patch (default: patch)',
    )
    parser.add_argument(
        '--node-tag-level',
        default=os.getenv('NODE_TAG_LEVEL', 'patch'),
        help='Node tag level: global, major, minor, or patch (default: patch)',
    )

    return parser.parse_args()


def main():
    args = parse_args()

    generator = ImageTagGenerator(
        python_version=args.python_version,
        python_image_variant=args.python_image_variant,
        poetry_version=args.poetry_version,
        uv_version=args.uv_version,
        nvm_version=args.nvm_version,
        node_version=args.node_version,
        python_tag_level=args.python_tag_level,
        poetry_tag_level=args.poetry_tag_level,
        uv_tag_level=args.uv_tag_level,
        nvm_tag_level=args.nvm_tag_level,
        node_tag_level=args.node_tag_level,
        compact_output=args.compact,
    )

    generator.generate_tags()
    generator.output_tags()


if __name__ == "__main__":
    main()
