#!/bin/sh

NVM_VERSION_INPUT="${1:-latest}"

NVM_DIR="${NVM_DIR:-/opt/nvm}"

# ---

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    DISTRO=$(awk -F= '/^ID=/{print $2}' /etc/os-release | tr -d '"')
else
    DISTRO='unknown'
fi

if [ "${DISTRO}" = 'alpine' ]; then
	echo "Sorry, Alpine Linux is not supported for nvm installation." >&2
	exit 1
fi

# ---

get_nvm_version() {
	local version="$1"
	local version_full="$(echo "${NVM_VERSION_INPUT}" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' || true)"
	if [ -n "${version_full}" ]; then
		echo "${version_full}"
		return 0
	fi
	local http_code
	local response
	if [ -z "${version}" ] || [ "${version}" = 'latest' ]; then
		response=$(curl -sSL -w "\n%{http_code}" "https://api.github.com/repos/nvm-sh/nvm/releases/latest")
		http_code=$(echo "${response}" | tail -n1)
		response=$(echo "${response}" | sed '$d')
		if [ "${http_code}" = "403" ] || [ "${http_code}" = "429" ]; then
			echo "GitHub API rate limit exceeded. Please try again later or use a personal access token." >&2
			return 1
		fi
		echo "${response}" \
			| sed -n 's/.*"tag_name": "\([^"]*\)".*/\1/p' \
			| sed 's/^v//'
	else
		response=$(curl -sSL -w "\n%{http_code}" "https://api.github.com/repos/nvm-sh/nvm/git/matching-refs/tags/v${version}")
		http_code=$(echo "${response}" | tail -n1)
		response=$(echo "${response}" | sed '$d')
		if [ "${http_code}" = "403" ] || [ "${http_code}" = "429" ]; then
			echo "GitHub API rate limit exceeded. Please try again later or use a personal access token." >&2
			return 1
		fi
		echo "${response}" \
			| sed -n 's/.*"ref": "\([^"]*\)".*/\1/p' \
			| sed 's|refs/tags/v||' \
			| sort -V \
			| tail -n1
	fi
}

NVM_VERSION="$(get_nvm_version "${NVM_VERSION_INPUT}")"
if [ -z "${NVM_VERSION}" ]; then
	echo "Failed to find a valid nvm version for '${NVM_VERSION_INPUT}'." >&2
	exit 1
fi

mkdir -p "${NVM_DIR}"

BASH_INSTALLED='false'
if ! command -v bash > /dev/null 2>&1; then
    if command -v apt-get > /dev/null 2>&1; then
		apt-get update && apt-get install -y --no-install-recommends bash || {
			echo "Failed to install bash temporarily, required to install nvm." >&2
			exit 1
		}
    elif command -v apk > /dev/null 2>&1; then
        apk add --no-cache bash || {
            echo "Failed to install bash temporarily, required to install nvm." >&2
            exit 1
        }
    else
        echo 'Bash is required to install nvm. No supported package manager found to install bash.' >&2
        exit 1
    fi
    echo 'Installed bash temporarily to install nvm.' >&2
	BASH_INSTALLED='true'
fi

NVM_INSTALLER_FILE="$(mktemp)"
curl "https://raw.githubusercontent.com/nvm-sh/nvm/v${NVM_VERSION}/install.sh" \
	-o "${NVM_INSTALLER_FILE}"
if [ $? -ne 0 ]; then
	echo "Failed to download nvm installer for version ${NVM_VERSION}." >&2
	exit 1
fi

BASH_ENV="/etc/bash_env"
touch "${BASH_ENV}"
if ! grep -q '. /etc/bash_env' /etc/bash.bashrc 2>/dev/null; then
	echo '. /etc/bash_env' >> /etc/bash.bashrc
fi

NVM_DIR="${NVM_DIR}" PROFILE="${BASH_ENV}" bash "${NVM_INSTALLER_FILE}"
if [ $? -ne 0 ]; then
	echo "Failed to install nvm." >&2
fi
rm -f "${NVM_INSTALLER_FILE}"

# Create user directories
while IFS= read -r dir; do
	mkdir -p "${NVM_DIR}/${dir}"
	chmod -R 777 "${NVM_DIR}/${dir}"
done <<EOF
.cache
alias
versions
EOF

echo "Installed nvm version ${NVM_VERSION} to ${NVM_DIR}."

if [ "${BASH_INSTALLED}" = 'true' ]; then
	if command -v apt-get > /dev/null 2>&1; then
		apt-get remove -y bash || {
			echo "Warning: Failed to uninstall bash." >&2
		}
	elif command -v apk > /dev/null 2>&1; then
		apk del bash || {
			echo "Warning: Failed to uninstall bash." >&2
		}
	fi
	echo "Uninstalled bash after installing nvm." >&2
fi
