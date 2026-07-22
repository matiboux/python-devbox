#!/bin/sh
set -e

# Script to install system development tools and dependencies.

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    DISTRO=$(awk -F= '/^ID=/{print $2}' /etc/os-release | tr -d '"')
else
    DISTRO='unknown'
fi

# Detect package manager based on distribution
PACKAGE_MANAGER=''
case "${DISTRO}" in
    alpine)
        PACKAGE_MANAGER="$(command -v apk)"
        ;;
    debian|ubuntu)
        PACKAGE_MANAGER="$(command -v apt-get)"
        ;;
esac

if [ -z "${PACKAGE_MANAGER}" ]; then
    echo "Unsupported distribution: ${DISTRO}" >&2
    exit 1
fi

PACKAGE_MANAGER_NAME="$(basename "${PACKAGE_MANAGER}")"

if [ "${PACKAGE_MANAGER_NAME}" = 'apk' ]; then

    # Install for Alpine Linux
    apk add --no-cache \
        build-base \
        ca-certificates \
        curl \
        git \
        jq \
        make \
        musl-dev \
        tmux \
        wget \
        yq

elif [ "${PACKAGE_MANAGER_NAME}" = 'apt-get' ]; then

    # Install for Debian/Ubuntu
    apt-get update
    apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
        jq \
        make \
        tmux \
        wget \
        yq

else

    echo "Unsupported package manager: ${PACKAGE_MANAGER_NAME}" >&2
    exit 1

fi
