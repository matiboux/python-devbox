#!/bin/sh
set -e

# Script to prepare the Devbox Python image.
# Orchestrates dynamic image building based on environment variables:
# - POETRY_VERSION: Version of Poetry to install if set
# - UV_VERSION: Version of uv to install if set
# - NVM_VERSION: Version of nvm to install if set
# - NODE_VERSION: Version of Node.js to install if set
# - USERNAME: Non-root username to create if set
# - USER_ID: Non-root user ID to create if set
# - GROUP_ID: Non-root group ID to create if set
# - SUDO_USER: Give sudo privileges to non-root user if true

COMMON_SCRIPTS_DIR="$(dirname "$(dirname "$0")")/common"

# Install system development tools
sh "${COMMON_SCRIPTS_DIR}/install-system-tools.sh"

# Install Python development tools
sh "${COMMON_SCRIPTS_DIR}/install-python-tools.sh"

if [ -n "${POETRY_VERSION}" ]; then
    # Install Poetry
    sh "${COMMON_SCRIPTS_DIR}/install-poetry.sh" "${POETRY_VERSION}"
fi

if [ -n "${UV_VERSION}" ]; then
    # Install uv
    sh "${COMMON_SCRIPTS_DIR}/install-uv.sh" "${UV_VERSION}"
fi

if [ -n "${NVM_VERSION}" ]; then
    # Install nvm
    sh "${COMMON_SCRIPTS_DIR}/install-nvm.sh" "${NVM_VERSION}"
fi

if [ -n "${NODE_VERSION}" ]; then
    # Install Node.js
    sh "${COMMON_SCRIPTS_DIR}/install-node.sh" "${NODE_VERSION}"
fi

if [ "${SUDO_USER}" = 'true' ]; then
    # Install sudo
    sh "${COMMON_SCRIPTS_DIR}/install-sudo.sh"
fi

if [ -n "${USERNAME}" ] || [ -n "${USER_ID}" ] || [ -n "${GROUP_ID}" ]; then
    # Create non-root user
    sh "${COMMON_SCRIPTS_DIR}/create-user.sh" "${USERNAME}" "${USER_ID}" "${GROUP_ID}" "${SUDO_USER}"
fi
