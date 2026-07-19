#!/bin/sh
set -e

USERNAME="$1"
USER_ID="$2"
GROUP_ID="$3"
SUDO_USER="$4"

if [ -z "${USERNAME}" ]; then
	USERNAME='user'
fi

if [ -z "${USER_ID}" ]; then
	USER_ID='1000'
fi

if [ -z "${GROUP_ID}" ]; then
	GROUP_ID='1000'
fi

if [ -z "${SUDO_USER}" ]; then
	SUDO_USER='false'
fi

# Create group and user
groupadd -g "${GROUP_ID}" "${USERNAME}"
useradd -lm -u "${USER_ID}" -g "${GROUP_ID}" "${USERNAME}"

# Add user to sudoers (if sudo is installed)
if [ "${SUDO_USER}" = 'true' ] && command -v sudo > /dev/null 2>&1; then
	usermod -aG sudo "${USERNAME}"
fi
