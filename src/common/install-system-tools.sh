#!/bin/sh
set -e

# Install system development tools and dependencies
apt-get update
apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    jq \
    make \
    tmux \
    wget \
    yq
