#!/bin/bash
set -euo pipefail

# Build Docker image with specified tags and versions

PYTHON_VERSION="${PYTHON_VERSION:-3.14.6}"
PYTHON_VARIANT="${PYTHON_VARIANT:-slim}"
POETRY_VERSION="${POETRY_VERSION:-}"
UV_VERSION="${UV_VERSION:-}"

REGISTRY_NAMESPACE="${REGISTRY_NAMESPACE:-matiboux}"
REGISTRY_REPOSITORY="${REGISTRY_REPOSITORY:-python-devbox}"

PROJECT_ROOT="$(dirname "$(dirname "$0")")"
DOCKERFILE="${PROJECT_ROOT}/Dockerfile"
if [ ! -f "${DOCKERFILE}" ]; then
    echo "Error: Dockerfile not found: ${DOCKERFILE}"
    exit 1
fi

PYTHON_IMAGE_TAG="${PYTHON_VERSION}-${PYTHON_VARIANT}"

BUILD_VARIANT='base'
if [ -n "$POETRY_VERSION" ] && [ -n "$UV_VERSION" ]; then
    BUILD_VARIANT='full'
elif [ -n "$POETRY_VERSION" ]; then
    BUILD_VARIANT='poetry'
elif [ -n "$UV_VERSION" ]; then
    BUILD_VARIANT='uv'
fi

IMAGE_TAG_ATOMIC="${REGISTRY_NAMESPACE}/${REGISTRY_REPOSITORY}:${PYTHON_IMAGE_TAG}"
if [ "$BUILD_VARIANT" == "full" ]; then
    IMAGE_TAG_ATOMIC="${IMAGE_TAG_ATOMIC}-full"
elif [ "$BUILD_VARIANT" == "poetry" ]; then
    IMAGE_TAG_ATOMIC="${IMAGE_TAG_ATOMIC}-poetry"
elif [ "$BUILD_VARIANT" == "uv" ]; then
    IMAGE_TAG_ATOMIC="${IMAGE_TAG_ATOMIC}-uv"
fi
if [ -n "$POETRY_VERSION" ]; then
    IMAGE_TAG_ATOMIC="${IMAGE_TAG_ATOMIC}-poetry${POETRY_VERSION}"
fi
if [ -n "$UV_VERSION" ]; then
    IMAGE_TAG_ATOMIC="${IMAGE_TAG_ATOMIC}-uv${UV_VERSION}"
fi

echo "Building image: $IMAGE_TAG_ATOMIC"
echo "  Python image: $PYTHON_IMAGE_TAG"
echo "  Build variant: $BUILD_VARIANT"
if [ -n "$POETRY_VERSION" ]; then
    echo "  Poetry: $POETRY_VERSION"
fi
if [ -n "$UV_VERSION" ]; then
    echo "  uv: $UV_VERSION"
fi

docker build \
    --build-arg "BUILD_VARIANT=${BUILD_VARIANT}" \
    --build-arg "PYTHON_VERSION=${PYTHON_VERSION}" \
    --build-arg "PYTHON_IMAGE_TAG=${PYTHON_IMAGE_TAG}" \
    --build-arg "POETRY_VERSION=${POETRY_VERSION}" \
    --build-arg "UV_VERSION=${UV_VERSION}" \
    --tag "$IMAGE_TAG_ATOMIC" \
    --file "$DOCKERFILE" \
    "$PROJECT_ROOT"
