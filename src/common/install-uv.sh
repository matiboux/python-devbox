#!/bin/sh

UV_VERSION_INPUT=${1:-latest}

# ---

UV_INSTALLER_FILE="$(mktemp)"

install_uv_and_exit() {
    sh "${UV_INSTALLER_FILE}"
    EXIT_CODE=$?
    if [ "${EXIT_CODE}" -ne 0 ]; then
        echo "Failed to install uv." >&2
    fi
    rm -f "${UV_INSTALLER_FILE}"
    exit ${EXIT_CODE}
}

# Set uv install parameters
export UV_NO_MODIFY_PATH='1'
export UV_UNMANAGED_INSTALL='/usr/local/bin'

# Try to install uv with the specified version
UV_VERSION_FULL="$(echo "${UV_VERSION_INPUT}" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' || true)"
if [ -n "${UV_VERSION_FULL}" ]; then
    curl -LsSf "https://astral.sh/uv/${UV_VERSION_FULL}/install.sh" -o "${UV_INSTALLER_FILE}"
    if [ $? -ne 0 ]; then
        echo "Failed to install uv version ${UV_VERSION_FULL}." >&2
        exit 1
    fi
    install_uv_and_exit
fi

get_uv_version() {
    local version="$1"
    if [ -z "${version}" ] || [ "${version}" = 'latest' ]; then
        pip index versions uv 2>/dev/null \
            | sed -n 's/^Available versions: //p' \
            | tr ',' '\n' \
            | sed 's/^ *//' \
            | head -n1
    else
        pip index versions uv 2>/dev/null \
            | sed -n 's/^Available versions: //p' \
            | tr ',' '\n' \
            | sed 's/^ *//' \
            | grep -E "^$(echo "${version}" | sed 's/\.*$//; s/\./\\./g')(\\.[0-9]+)*$" \
            | head -n1
    fi
}

# Install uv with the inferred version
UV_VERSION_INFERRED="$(get_uv_version "${UV_VERSION_INPUT}")"
if [ -n "${UV_VERSION_INFERRED}" ]; then
    curl -LsSf "https://astral.sh/uv/${UV_VERSION_INFERRED}/install.sh" -o "${UV_INSTALLER_FILE}"
    if [ $? -ne 0 ]; then
        echo "Failed to install uv version ${UV_VERSION_INFERRED}." >&2
        exit 1
    fi
    install_uv_and_exit
fi

echo "Failed to find a valid uv version for '${UV_VERSION_INPUT}'." >&2
exit 1
