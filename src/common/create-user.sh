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

# Create group
if command -v groupadd > /dev/null 2>&1; then
	groupadd -g "${GROUP_ID}" "${USERNAME}"
elif command -v addgroup > /dev/null 2>&1; then
	addgroup -g "${GROUP_ID}" "${USERNAME}"
else
	echo "No suitable command found to create group" >&2
	exit 1
fi

# Create user
if command -v useradd > /dev/null 2>&1; then
	useradd -lm -u "${USER_ID}" -g "${GROUP_ID}" "${USERNAME}"
elif command -v adduser > /dev/null 2>&1; then
	adduser -D -u "${USER_ID}" -G "${USERNAME}" "${USERNAME}"
else
	echo "No suitable command found to create user" >&2
	exit 1
fi

# Add user to sudoers
if [ "${SUDO_USER}" = 'true' ]; then

	# Detect Linux distribution
	if [ -f /etc/os-release ]; then
		DISTRO=$(awk -F= '/^ID=/{print $2}' /etc/os-release | tr -d '"')
	else
		DISTRO='unknown'
	fi

	# Detect sudo command based on distribution
	SUDO_COMMAND=''
	case "${DISTRO}" in
		alpine)
			SUDO_COMMAND="$(command -v doas || command -v sudo)"
			;;
		debian|ubuntu)
			SUDO_COMMAND="$(command -v sudo || command -v doas)"
			;;
	esac

	if [ -z "${SUDO_COMMAND}" ]; then
		echo "Unsupported distribution: ${DISTRO}" >&2
		exit 1
	fi

	SUDO_COMMAND_NAME="$(basename "${SUDO_COMMAND}")"

	if [ "${SUDO_COMMAND_NAME}" = 'sudo' ]; then

		if ! getent group sudo > /dev/null 2>&1; then
			echo "Group 'sudo' does not exist" >&2
			return 1
		fi

		if command -v usermod > /dev/null 2>&1; then
			usermod -aG sudo "${USERNAME}"
		elif command -v adduser > /dev/null 2>&1; then
			adduser "${USERNAME}" sudo
		else
			echo "No suitable command found to add user to sudo group" >&2
			return 1
		fi

	elif [ "${SUDO_COMMAND_NAME}" = 'doas' ]; then

		if ! getent group wheel > /dev/null 2>&1; then
			echo "Group 'wheel' does not exist" >&2
			return 1
		fi

		if command -v usermod > /dev/null 2>&1; then
			usermod -aG wheel "${USERNAME}"
		elif command -v adduser > /dev/null 2>&1; then
			adduser "${USERNAME}" wheel
		else
			echo "No suitable command found to add user to wheel group" >&2
			return 1
		fi

	else

		echo "Unsupported sudo command: ${SUDO_COMMAND_NAME}" >&2
		exit 1

	fi

fi
