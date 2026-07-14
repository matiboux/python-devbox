#!/bin/sh
set -e

# Install sudo
apt-get update
apt-get install -y --no-install-recommends sudo

# Allow members of group 'sudo' to execute commands without a password
echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
