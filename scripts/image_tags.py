#!/usr/bin/env python3

import argparse
import os
import sys
from itertools import product
from typing import List, Sequence, Tuple


class ImageTagGenerator:

    def __init__(
        self,
        components: Sequence[Tuple[str, str] | Tuple[str, str, str]],
        python_image_variant: str = '',
        compact_output: bool = False,
    ):
        """
        Initialize the ImageTagGenerator with component versions and tag levels.
        :param components: List of tuples containing (component_name, version, tag_level)
        :param python_image_variant: Python image variant: empty, slim, or alpine
        :param compact_output: If True, output tags as comma-separated values on a single line
        """
        self.components: List[Tuple[str, str, str]] = [
            (
                (comp[0], comp[1], self._validate_tag_level(comp[2]))
                if len(comp) >= 3 else
                (comp[0], comp[1], 'patch')
            )
            for comp in components
        ]
        self.python_image_variant: str = python_image_variant
        self.compact_output: bool = compact_output

        self.image_tags: List[str] = []

    @staticmethod
    def _validate_tag_level(level: str) -> str:
        if level in ('global', 'major', 'minor', 'patch'):
            return level
        return 'patch'

    def _get_component_options(self, version: str, level: str) -> List[str]:

        if not version:
            return ['']

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

        component_options_list = []
        for comp_name, comp_version, comp_tag_level in self.components:
            if comp_name == 'python':
                options = self._get_component_options(comp_version, comp_tag_level)
            else:
                options = self._get_prefixed_options(comp_name, comp_version, comp_tag_level)
            component_options_list.append(options)
            print(f"{comp_name.capitalize()} component options: {options}", file=sys.stderr)

        tags: List[str] = []
        for component_values in product(*component_options_list):
            tag_pieces: List[str] = []

            for i, (comp_name, _, _) in enumerate(self.components):
                if component_values[i]:
                    tag_pieces.append(component_values[i])
                if comp_name == 'python' and self.python_image_variant:
                    tag_pieces.append(self.python_image_variant)

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

    components: List[Tuple[str, str, str]] = [
        ('python', args.python_version, args.python_tag_level),
        ('node', args.node_version, args.node_tag_level),
        ('poetry', args.poetry_version, args.poetry_tag_level),
        ('uv', args.uv_version, args.uv_tag_level),
        ('nvm', args.nvm_version, args.nvm_tag_level),
    ]

    generator = ImageTagGenerator(
        components=components,
        python_image_variant=args.python_image_variant,
        compact_output=args.compact,
    )

    generator.generate_tags()
    generator.output_tags()


if __name__ == "__main__":
    main()
