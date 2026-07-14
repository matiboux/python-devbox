#!/bin/sh
set -e

USER=${1:-user}
UID=${2:-1000}
GID=${3:-1000}

groupadd -g ${GID} ${USER}
useradd -lm -u ${UID} -g ${GID} ${USER}
