#!/bin/bash
set -euo pipefail
PLIST="$HOME/Library/LaunchAgents/com.akses.devicesync.plist"
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
rm -f "$PLIST"
rm -rf "$HOME/Applications/Sync.app"
echo 'Removed Sync.app and its daily schedule.'
echo 'Kept configuration and dependencies: ~/Library/Application Support/akses-sync'
echo 'Kept cache: ~/.akses_sync_cache.json and logs: ~/Library/Logs/akses-sync.log'
