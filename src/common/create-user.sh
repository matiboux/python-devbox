#!/bin/sh
set -e

USER=${1:-user}
UID=${2:-1000}
GID=${3:-1000}
SUDOER=${4:-true}

# Create group and user
groupadd -g ${GID} ${USER}
useradd -lm -u ${UID} -g ${GID} ${USER}

# Add user to sudoers (if sudo is installed)
if [ "${SUDOER}" = 'true' ] && command -v sudo > /dev/null 2>&1; then
	usermod -aG sudo ${USER}
fi
