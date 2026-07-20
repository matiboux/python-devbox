#!/bin/sh

NVM_VERSION_INPUT=${1:-latest}

# ---

NVM_INSTALLER_FILE="$(mktemp)"

download_nvm_installer() {
    local version="$1"
    curl "https://raw.githubusercontent.com/nvm-sh/nvm/v${version}/install.sh" \
        -o "${NVM_INSTALLER_FILE}"
    return $?
}

install_nvm_and_exit() {
    bash "${NVM_INSTALLER_FILE}"
    EXIT_CODE=$?
    if [ "${EXIT_CODE}" -ne 0 ]; then
        echo "Failed to install nvm." >&2
    fi
    rm -f "${NVM_INSTALLER_FILE}"
    exit ${EXIT_CODE}
}

# Try to install nvm with the specified version
NVM_VERSION_FULL="$(echo "${NVM_VERSION_INPUT}" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' || true)"
if [ -n "${NVM_VERSION_FULL}" ]; then
    download_nvm_installer "${NVM_VERSION_FULL}"
    if [ $? -ne 0 ]; then
        echo "Failed to download nvm installer for version ${NVM_VERSION_FULL}." >&2
        exit 1
    fi
    install_nvm_and_exit
fi

get_nvm_version() {
    local version="$1"
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

# Install nvm with the inferred version
NVM_VERSION_INFERRED="$(get_nvm_version "${NVM_VERSION_INPUT}")"
if [ -n "${NVM_VERSION_INFERRED}" ]; then
    download_nvm_installer "${NVM_VERSION_INFERRED}"
    if [ $? -ne 0 ]; then
        echo "Failed to download nvm installer for version ${NVM_VERSION_INFERRED}." >&2
        exit 1
    fi
    install_nvm_and_exit
fi

echo "Failed to find a valid nvm version for '${NVM_VERSION_INPUT}'." >&2
exit 1
