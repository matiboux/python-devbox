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
        wget

# Install Python development tools
RUN pip install --no-cache-dir ruff


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
RUN export POETRY_HOME='/usr/local' && \
    export POETRY_VERSION="${POETRY_VERSION}" && \
    curl -sSL https://install.python-poetry.org | python3 -


# --
# Python Devbox with uv

FROM python_base AS python_devbox_uv

# Build arguments
ARG UV_VERSION

# Install uv (Python package manager)
RUN export UV_NO_MODIFY_PATH='1' && \
    export UV_UNMANAGED_INSTALL='/usr/local/bin' && \
    curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh


# --
# Python Devbox with uv and Poetry

FROM python_base AS python_devbox_full

# Build arguments
ARG POETRY_VERSION
ARG UV_VERSION

# Install Poetry (Python dependency manager)
RUN export POETRY_HOME='/usr/local' && \
    export POETRY_VERSION="${POETRY_VERSION}" && \
    curl -sSL https://install.python-poetry.org | python3 -

# Install uv (Python package manager)
RUN export UV_NO_MODIFY_PATH='1' && \
    export UV_UNMANAGED_INSTALL='/usr/local/bin' && \
    curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh


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
