#!/bin/sh
set -e

NODE_VERSION_INPUT="${1:-lts}"

NVM_DIR="${NVM_DIR:-/opt/nvm}"

# ---

if [ ! -s "${NVM_DIR}/nvm.sh" ]; then
    echo 'Cannot find nvm. Please install nvm before installing Node.js.' >&2
    exit 1
fi
\. "${NVM_DIR}/nvm.sh"

if [ -z "${NODE_VERSION_INPUT}" ] || [ "${NODE_VERSION_INPUT}" = 'lts' ]; then

    # Install latest LTS version of Node.js
    nvm install --lts --latest-npm --default

elif [ "${NODE_VERSION_INPUT}" = 'latest' ]; then

    # Install latest version of Node.js
    nvm install node --latest-npm --default

else

    # Install specific version of Node.js
    nvm install "${NODE_VERSION_INPUT}" --latest-npm --default

fi
