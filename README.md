# Sync for macOS

Sync.app backs up images from your Mac to your akses server. It scans Photos,
Desktop, Downloads, Documents, iCloud Drive, Messages attachments, and supported
WhatsApp/Telegram folders, then uploads them to the server. Use your own Mac and account.

## Install on another MacBook

Requires macOS 12 or later, Python 3 (with pip and venv), and an internet connection.
Install Python from https://www.python.org/downloads/macos/ if needed.
In Terminal, run:

```bash
curl -fL https://raw.githubusercontent.com/Masozee/akses/main/scripts/install-sync.sh -o /tmp/install-akses-sync.sh && bash /tmp/install-akses-sync.sh
```

The installer downloads this repository, asks for your server URL and credentials,
installs Python dependencies in a dedicated virtual environment, installs
`~/Applications/Sync.app`, and schedules it daily at **03:00 local time** using
LaunchAgents. You must be logged in for the schedule to run. Installation does
not start a sync. Rerunning the installer updates the app and keeps configuration.

Credentials are stored locally in
`~/Library/Application Support/akses-sync/config.json` with owner-only permissions.
They are not included in GitHub. Edit this file to change the server or account.

Grant Full Disk Access in **System Settings → Privacy & Security** to the app and
the Python interpreter path printed by the installer. macOS may also request
Photos/automation permissions on the first run. Permissions must be granted manually.

This is a Python-backed app bundle, not a standalone signed/notarized binary.
Dependencies are installed separately on each Mac, for its native architecture.

## Run and manage

```bash
# Upload at most five new images (this is a real upload).
"$HOME/Applications/Sync.app/Contents/MacOS/sync" --limit=5

# Inspect candidates without uploading images (still logs into the server).
"$HOME/Applications/Sync.app/Contents/MacOS/sync" --dry-run

# Read logs.
tail -f "$HOME/Library/Logs/akses-sync.log"
```

To uninstall, download/clone this repository and run `bash Sync-dist/uninstall.sh`.
Uninstall removes the app and schedule but keeps your configuration, virtual
environment, cache, and logs. To remove saved credentials and dependencies too,
delete `~/Library/Application Support/akses-sync`.

If the repository is private, use an authenticated Git client to clone it, then
run `bash Sync-dist/install.sh`; the public download command requires a public repo.
