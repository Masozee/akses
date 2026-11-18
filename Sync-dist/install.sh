#!/bin/bash
set -euo pipefail
[[ "$(uname -s)" == Darwin ]] || { echo 'This installer requires macOS.' >&2; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"
APP_DST="$HOME/Applications/Sync.app"
SUPPORT="$HOME/Library/Application Support/akses-sync"
PLIST="$HOME/Library/LaunchAgents/com.akses.devicesync.plist"
PY="$(command -v python3 || true)"
if [[ -z "$PY" ]]; then
    echo 'Install Python 3 from https://www.python.org/downloads/macos/ and rerun this installer.' >&2
    exit 1
fi
"$PY" "$HERE/configure.py"
mkdir -p "$SUPPORT" "$HOME/Applications" "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
"$PY" -m venv "$SUPPORT/venv"
"$SUPPORT/venv/bin/python3" -m pip install requests osxphotos pyobjc-framework-Cocoa
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
# ditto preserves the app bundle's permissions.
ditto "$HERE/Sync.app" "$APP_DST"
chmod +x "$APP_DST/Contents/MacOS/sync"
"$PY" - "$APP_DST" "$PLIST" <<'PY'
import plistlib
import sys
from pathlib import Path
app, target = sys.argv[1:]
log = str(Path.home() / "Library/Logs/akses-sync.log")
with open(target, "wb") as file:
    plistlib.dump({
        "Label": "com.akses.devicesync",
        "ProgramArguments": [app + "/Contents/MacOS/sync"],
        "StartCalendarInterval": {"Hour": 3, "Minute": 0},
        "RunAtLoad": True,
        "StandardOutPath": log,
        "StandardErrorPath": log,
        "ProcessType": "Background",
    }, file)
PY
plutil -lint "$PLIST"
launchctl bootstrap "gui/$(id -u)" "$PLIST"
# RunAtLoad already fires one sync on bootstrap; kickstart guarantees it even if
# the agent was already loaded (reinstall/upgrade).
launchctl kickstart "gui/$(id -u)/com.akses.devicesync" 2>/dev/null || true
echo "Installed: $APP_DST"
echo 'First sync started now, and scheduled daily at 03:00 local time while logged in.'
echo 'In System Settings > Privacy & Security > Full Disk Access, add:'
echo "  $APP_DST"
echo "  $SUPPORT/venv/bin/python3"
echo '  (without Full Disk Access the first run only sees Desktop/Downloads; grant it, then the 03:00 run covers Photos/Messages.)'
echo "Run manually: \"$APP_DST/Contents/MacOS/sync\" --limit=5"
echo 'Logs: ~/Library/Logs/akses-sync.log'
