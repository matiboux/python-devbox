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
    if [ -z "${version}" ] || [ "${version}" = 'latest' ]; then
        curl -sSL "https://api.github.com/repos/nvm-sh/nvm/releases/latest" \
            | grep -Po '"tag_name": "\K.*?(?=")' \
            | sed 's/^v//'
    else
        local tags_page=1
        local inferred_version=''
        while [ -z "${inferred_version}" ]; do
            inferred_version="$(
                curl -sSL "https://api.github.com/repos/nvm-sh/nvm/tags?per_page=100&page=${tags_page}" \
                    | grep -Po '"name": "\K.*?(?=")' \
                    | sed 's/^v//' \
                    | grep -E "^$(echo "${version}" | sed 's/\.*$//; s/\./\\./g')(\\.[0-9]+)*$" \
                    | head -n1
            )"
            tags_page=$((tags_page + 1))
        done
        echo "${inferred_version}"
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
