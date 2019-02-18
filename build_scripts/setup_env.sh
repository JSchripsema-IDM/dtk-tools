#!/usr/bin/env bash

SRC_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
# Takes in the username and password for packages.idmod.org and creates a pypirc in users home directory

echo "Setting up pip conf"
cp "${SRC_DIR}/pip.conf" ~/pip.conf

echo "Setting up pypirc"
cp "${SRC_DIR}/.pypirc" ~/.pypirc
echo "Replacing <username> with ${bamboo_UserArtifactory}"
sed -i "s|<username>|${bamboo_UserArtifactory}|" ~/.pypirc
sed -i "s|<password>|${bamboo_PasswordArtifactory}|" ~/.pypirc