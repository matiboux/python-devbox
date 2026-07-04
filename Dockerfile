#syntax=docker/dockerfile:1

# This Dockerfile uses the service folder as context.


# ----------------
# Global
# ----------------

# --
# Global build arguments

ARG BUILD_VARIANT=base
ARG PYTHON_VERSION=3.14.6
ARG PYTHON_IMAGE_TAG=3.14.6
ARG POETRY_VERSION=2.4.1
ARG UV_VERSION=0.11.26
ARG USER=user
ARG UID=1000
ARG GID=1000

# --
# Upstream images

FROM python:${PYTHON_VERSION} AS python_upstream


# ----------------
# Base stages
# ----------------

# --
# Python base stage

FROM python_upstream AS python_base

# Install system development tools and dependencies
# (hadolint: Ignore non-pinned apt package version)
# hadolint ignore=DL3008
RUN --mount=type=cache,sharing=locked,id=apt-cache,target=/var/cache/apt \
	--mount=type=cache,sharing=locked,id=apt-lib,target=/var/lib/apt \
	apt-get update && \
	apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        make \
        tmux \
        wget

# Install Python development tools
RUN pip install --no-cache-dir ruff pytest


# ----------------
# Python Devbox variants
# ----------------

# --
# Python Devbox base

FROM python_base AS python_devbox_base


# --
# Python Devbox with Poetry

FROM python_base AS python_devbox_poetry

# Build arguments
ARG POETRY_VERSION

# Install Poetry (Python dependency manager)
RUN <<EOF
export POETRY_HOME='/usr/local'
export POETRY_VERSION="${POETRY_VERSION}"
POETRY_INSTALLER_FILE="$(mktemp)"
curl -sSL https://install.python-poetry.org -o "${POETRY_INSTALLER_FILE}"
python3 "${POETRY_INSTALLER_FILE}"
if [ $? -ne 0 ]; then
    export POETRY_VERSION="$(
        pip index versions poetry 2>/dev/null \
        | sed -n 's/^Available versions: //p' \
        | tr ',' '\n' \
        | sed 's/^ *//' \
        | grep -E "^$(echo "${POETRY_VERSION}" | sed 's/\.*$//; s/\./\\./g')(\\.[0-9]+)*$" \
        | head -n1
    )"
    python3 "${POETRY_INSTALLER_FILE}"
fi
rm -f "${POETRY_INSTALLER_FILE}"
EOF


# --
# Python Devbox with uv

FROM python_base AS python_devbox_uv

# Build arguments
ARG UV_VERSION

# Install uv (Python dependency manager)
RUN <<EOF
export UV_NO_MODIFY_PATH='1'
export UV_UNMANAGED_INSTALL='/usr/local/bin'
UV_INSTALLER_FILE="$(mktemp)"
curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" -o "${UV_INSTALLER_FILE}"
if [ $? -ne 0 ]; then
    UV_VERSION="$(
        pip index versions uv 2>/dev/null \
        | sed -n 's/^Available versions: //p' \
        | tr ',' '\n' \
        | sed 's/^ *//' \
        | grep -E "^$(echo "${UV_VERSION}" | sed 's/\.*$//; s/\./\\./g')(\\.[0-9]+)*$" \
        | head -n1
    )"
    curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" -o "${UV_INSTALLER_FILE}"
fi
sh "${UV_INSTALLER_FILE}"
rm -f "${UV_INSTALLER_FILE}"
EOF


# --
# Python Devbox with uv and Poetry

FROM python_base AS python_devbox_full

# Build arguments
ARG POETRY_VERSION
ARG UV_VERSION

# Install Poetry (Python dependency manager)
RUN <<EOF
export POETRY_HOME='/usr/local'
export POETRY_VERSION="${POETRY_VERSION}"
POETRY_INSTALLER_FILE="$(mktemp)"
curl -sSL https://install.python-poetry.org -o "${POETRY_INSTALLER_FILE}"
python3 "${POETRY_INSTALLER_FILE}"
if [ $? -ne 0 ]; then
    export POETRY_VERSION="$(
        pip index versions poetry 2>/dev/null \
        | sed -n 's/^Available versions: //p' \
        | tr ',' '\n' \
        | sed 's/^ *//' \
        | grep -E "^$(echo "${POETRY_VERSION}" | sed 's/\.*$//; s/\./\\./g')(\\.[0-9]+)*$" \
        | head -n1
    )"
    python3 "${POETRY_INSTALLER_FILE}"
fi
rm -f "${POETRY_INSTALLER_FILE}"
EOF

# Install uv (Python dependency manager)
RUN <<EOF
export UV_NO_MODIFY_PATH='1'
export UV_UNMANAGED_INSTALL='/usr/local/bin'
UV_INSTALLER_FILE="$(mktemp)"
curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" -o "${UV_INSTALLER_FILE}"
if [ $? -ne 0 ]; then
    UV_VERSION="$(
        pip index versions uv 2>/dev/null \
        | sed -n 's/^Available versions: //p' \
        | tr ',' '\n' \
        | sed 's/^ *//' \
        | grep -E "^$(echo "${UV_VERSION}" | sed 's/\.*$//; s/\./\\./g')(\\.[0-9]+)*$" \
        | head -n1
    )"
    curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" -o "${UV_INSTALLER_FILE}"
fi
sh "${UV_INSTALLER_FILE}"
rm -f "${UV_INSTALLER_FILE}"
EOF


# ----------------
# Python Devbox image
# ----------------

# --
# Python Devbox image

FROM python_devbox_${BUILD_VARIANT} AS python_devbox

# Build arguments
ARG USER
ARG UID
ARG GID

# Create non-root user
RUN groupadd -g ${GID} ${USER} && \
    useradd -lm -u ${UID} -g ${GID} ${USER}

# Run as created non-root user
USER ${USER}
WORKDIR /home/${USER}

ENTRYPOINT ["/bin/bash"]
CMD []
