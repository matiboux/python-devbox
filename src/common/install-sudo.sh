#!/bin/sh
set -e

# Script to install sudo.

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
    apk add --no-cache doas doas-sudo-shim

	# Allow members of group 'wheel' to execute commands without a password
	echo 'permit nopass :wheel' >> /etc/doas.conf

elif [ "${PACKAGE_MANAGER_NAME}" = 'apt-get' ]; then

    # Install for Debian/Ubuntu
	apt-get update
	apt-get install -y --no-install-recommends sudo

	# Allow members of group 'sudo' to execute commands without a password
	echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

else

    echo "Unsupported package manager: ${PACKAGE_MANAGER_NAME}" >&2
    exit 1

fi
