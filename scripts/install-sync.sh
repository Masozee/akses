#!/bin/bash
# Download the Sync distribution from GitHub and install it for this user.
set -euo pipefail
[[ "$(uname -s)" == Darwin ]] || { echo 'This installer requires macOS.' >&2; exit 1; }
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
URL='https://github.com/Masozee/akses/archive/refs/heads/main.tar.gz'
echo 'Downloading Sync from Masozee/akses...'
curl --fail --location --show-error --silent --proto '=https' --tlsv1.2 "$URL" -o "$WORK/sync.tar.gz"
tar -xzf "$WORK/sync.tar.gz" -C "$WORK"
bash "$WORK/akses-main/Sync-dist/install.sh"
