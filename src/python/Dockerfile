#syntax=docker/dockerfile:1

# This Dockerfile uses the root folder as context.


# ----------------
# Global
# ----------------

# --
# Global build arguments

ARG BUILD_VARIANT=base
ARG PYTHON_VERSION=3.14.6
ARG PYTHON_IMAGE_VARIANT=
ARG POETRY_VERSION=
ARG UV_VERSION=
ARG USERNAME=user
ARG USER_ID=1000
ARG GROUP_ID=1000
ARG SUDO_USER=true


# --
# Upstream images

FROM python:${PYTHON_VERSION}${PYTHON_IMAGE_VARIANT:+-${PYTHON_IMAGE_VARIANT}} AS python_upstream


# ----------------
# Devbox Python
# ----------------

FROM python_upstream AS devbox_python

# Build arguments
ARG BUILD_VARIANT
ARG PYTHON_IMAGE_VARIANT
ARG PYTHON_VERSION
ARG PYTHON_IMAGE_TAG
ARG POETRY_VERSION
ARG UV_VERSION
ARG USERNAME
ARG USER_ID
ARG GROUP_ID
ARG SUDO_USER

# Run installation script for Devbox Python image
RUN --mount=type=bind,source=./src/common,target=/tmp/devbox/common \
    --mount=type=bind,source=./src/python,target=/tmp/devbox/python \
    --mount=type=cache,sharing=locked,id=apt-cache,target=/var/cache/apt \
	--mount=type=cache,sharing=locked,id=apt-lib,target=/var/lib/apt \
	sh /tmp/devbox/python/install-python.sh

# Run as created non-root user
USER ${USERNAME}
WORKDIR /home/${USERNAME}

COPY --link --chmod=755 ./src/common/entrypoint-shell.sh /usr/local/bin/devbox-entrypoint
ENTRYPOINT ["/usr/local/bin/devbox-entrypoint"]
CMD []
