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

## Windows version

Requires Windows 10/11, Windows PowerShell 5.1+, and Python 3.10+ with pip/venv.
Install Python from https://www.python.org/downloads/windows/ first.
Run this in **PowerShell as your normal user**:

```powershell
Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/Masozee/akses/main/scripts/install-sync.ps1' -OutFile "$env:TEMP\install-akses-sync.ps1"; powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\install-akses-sync.ps1"
```

Alternatively, download/extract this repository and run
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Windows-dist\install.ps1`.
The execution-policy override applies only to that process; managed Windows policy
may prevent unsigned scripts from running.

The installer prompts for your server/account, installs into
`%LOCALAPPDATA%\akses-sync`, creates **Akses Sync** in the Start menu, and registers
a per-user daily **03:00** task. Windows must be awake, you must be logged in, and
Task Scheduler's default battery restrictions apply. No sync runs during installation.
The task uses an interactive user principal and prevents overlapping scheduled runs;
see [Microsoft's task settings documentation](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasksettingsset).

Windows scans Desktop, Downloads, Documents and Pictures, resolving redirected
folders such as OneDrive. Edit `scan_dirs` in the local `config.json` to add or
remove folders. Cloud-only files may download when opened; ensure intended images
are available offline. Windows does not read Apple Photos databases or macOS chat
containers. All candidate images go to the server before its filtering occurs.

Credentials are plaintext in local `config.json`, protected by a Windows ACL
restricted to your user and SYSTEM. Reinstall preserves configuration. This is a
Python-backed Windows application, not a standalone signed `.exe`.

```powershell
# Preview candidates; contacts the server but does not upload images.
& "$env:LOCALAPPDATA\akses-sync\venv\Scripts\python.exe" "$env:LOCALAPPDATA\akses-sync\run-sync.py" --dry-run

# Upload at most five new images.
& "$env:LOCALAPPDATA\akses-sync\venv\Scripts\python.exe" "$env:LOCALAPPDATA\akses-sync\run-sync.py" --limit=5

# View logs.
Get-Content "$env:LOCALAPPDATA\akses-sync\sync.log" -Tail 50

# Uninstall (keeps credentials, cache and logs; add -Purge to delete them).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\akses-sync\uninstall.ps1"
```

Offline tests: `python3 -m unittest discover -s tests -v`.
Platform selection, Windows configuration encoding, scan deduplication, cache
storage, and existing Mac paths are covered. Native Windows installation, folder
ACLs, shortcuts, and Task Scheduler still require validation on Windows.
