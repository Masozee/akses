#!/usr/bin/env python3
"""Create private per-user configuration without putting credentials in Git."""
import getpass
import json
import os
from pathlib import Path
from urllib.parse import urlparse

path = Path.home() / "Library/Application Support/akses-sync/config.json"
if path.exists():
    print(f"Using existing configuration: {path}")
else:
    print("Sync uploads images from Photos, Desktop, Downloads, Documents, iCloud Drive,")
    print("Messages, and supported chat folders to your akses server.")
    print("The server filters uploads for a personal NSFW backup. Use only your own account and Mac.")
    url = input("Server URL [https://apiresto.kapulaga.net]: ").strip() or "https://apiresto.kapulaga.net"
    if urlparse(url).scheme != "https" or not urlparse(url).netloc:
        raise SystemExit("Enter a valid HTTPS server URL.")
    email = input("Account email: ").strip()
    password = getpass.getpass("Account password: ")
    if not email or not password:
        raise SystemExit("Email and password are required.")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as file:
        json.dump(dict(base_url=url.rstrip("/"), email=email, password=password), file)
    print(f"Saved private configuration: {path}")
