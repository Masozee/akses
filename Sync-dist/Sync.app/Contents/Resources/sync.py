#!/usr/bin/env python3
"""Scan common image locations on this Mac and sync them to the akses backend.

Server keeps only images its NSFW detector flags; everything else is discarded there.
A local cache skips files already processed so non-NSFW images aren't re-uploaded daily.
"""
import sys, os, json, time, requests, hashlib, mimetypes, tempfile, shutil
from pathlib import Path

# The python.org framework interpreter shows a Dock icon as soon as AppKit/Photos
# automation loads. Mark the process as a background accessory so no icon appears.
try:
    from AppKit import NSApplication, NSApplicationActivationPolicyProhibited
    NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyProhibited)
except Exception:
    pass

CONFIG_FILE = Path.home() / "Library/Application Support/akses-sync/config.json"
try:
    config = json.loads(CONFIG_FILE.read_text())
    BASE_URL = config["base_url"].rstrip("/")
    EMAIL = config["email"]
    PASSWORD = config["password"]
except (OSError, ValueError, KeyError):
    raise SystemExit("Sync is not configured. Run the Sync installer first.")

HOME = Path.home()
LIBRARY = str(HOME / "Pictures/Photos Library.photoslibrary")
CACHE_FILE = HOME / ".akses_sync_cache.json"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".gif", ".bmp", ".tiff", ".tif"}
MAX_BYTES = 50 * 1024 * 1024  # skip files larger than 50MB
MIN_BYTES = 50 * 1024         # skip files smaller than 50KB (app icons, thumbnails)

# Filesystem roots to walk for image files. Missing paths are skipped silently.
SCAN_DIRS = [
    HOME / "Desktop",
    HOME / "Downloads",
    HOME / "Documents",
    HOME / "Library/Mobile Documents/com~apple~CloudDocs",   # iCloud Drive
    HOME / "Library/Messages/Attachments",                   # Messages
]
# Chat-app media live under container globs that vary by version.
SCAN_GLOBS = [
    "Library/Group Containers/*.whatsapp*/**/Media",
    "Library/Group Containers/*.whatsapp*/**/Media/**",
    "Library/Group Containers/*telegram*/**",
]

# Directory names never worth scanning (build junk, caches, VCS).
SKIP_DIR_NAMES = {".git", "node_modules", ".Trash", "Caches", ".cache", "__pycache__", "DerivedData"}

http = requests.Session()
# Cloudflare returns 502 for the default python-requests User-Agent.
http.headers["User-Agent"] = "akses-device-sync/1.0"


def login():
    r = http.post(f"{BASE_URL}/api/auth/login/",
                  json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    r.raise_for_status()
    return r.json()["access"]


def check_existing(token, asset_ids):
    """Return the set of device_asset_ids already stored on the server (chunked)."""
    existing = set()
    headers = {"Authorization": f"Bearer {token}"}
    for i in range(0, len(asset_ids), 500):
        chunk = asset_ids[i:i + 500]
        r = http.post(f"{BASE_URL}/api/images/check_existing/",
                      headers=headers, json={"ids": chunk}, timeout=30)
        r.raise_for_status()
        existing.update(r.json().get("existing", []))
    return existing


def upload_image(token, filepath, filename, asset_id):
    mime = mimetypes.guess_type(filename)[0] or "image/jpeg"
    with open(filepath, "rb") as f:
        return http.post(
            f"{BASE_URL}/api/images/",
            headers={"Authorization": f"Bearer {token}"},
            data={"title": filename, "image_type": "photo",
                  "device_asset_id": asset_id, "device_id": "device-sync"},
            files={"original_image": (filename, f, mime)},
            timeout=120,
        )


def load_cache():
    try:
        return json.loads(CACHE_FILE.read_text())
    except Exception:
        return {}


def save_cache(cache):
    try:
        CACHE_FILE.write_text(json.dumps(cache))
    except Exception as e:
        print(f"  warning: cache not saved: {e}")


def fs_key(path):
    """Stable per-file identity for the local cache: path + size + mtime."""
    st = os.stat(path)
    return f"{path}:{st.st_size}:{int(st.st_mtime)}"


def fs_asset_id(path):
    """Stable device_asset_id for a filesystem image (path-based)."""
    return "fs:" + hashlib.sha1(str(path).encode()).hexdigest()


def iter_fs_images():
    """Yield absolute paths of image files across the configured roots."""
    roots = [d for d in SCAN_DIRS if d.exists()]
    for pat in SCAN_GLOBS:
        roots += [p for p in HOME.glob(pat) if p.is_dir()]
    seen_roots = set()
    for root in roots:
        rp = os.path.realpath(root)
        if rp in seen_roots or LIBRARY in rp:
            continue
        seen_roots.add(rp)
        for dirpath, dirnames, filenames in os.walk(root):
            if ".photoslibrary" in dirpath:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES and not d.endswith(".photoslibrary")]
            for name in filenames:
                if os.path.splitext(name)[1].lower() in IMAGE_EXTS:
                    yield os.path.join(dirpath, name)


def ensure_local(photo, download_dir):
    """Path to a Photos original, downloading from iCloud if missing. (path, is_temp)."""
    if photo.path and os.path.exists(photo.path):
        return photo.path, False
    exported = photo.export(download_dir, use_photos_export=True, timeout=180)
    if exported and os.path.exists(exported[0]):
        return exported[0], True
    return None, False


def collect_photos():
    """Own Photos-library images (skip Shared Album / 'Shared with You')."""
    try:
        import osxphotos
    except ImportError:
        print("  osxphotos not installed — skipping Photos library")
        return []
    if not os.path.exists(LIBRARY):
        return []
    db = osxphotos.PhotosDB(dbfile=LIBRARY)
    return [p for p in db.photos() if not p.ismovie and not p.shared]


def sync(dry_run=False, limit=None):
    token = login()
    print("Logged in successfully")
    cache = load_cache()

    # --- gather filesystem images (skip ones unchanged since last run) ---
    fs_items = []   # (asset_id, filename, path, cache_key)
    fs_skipped_cache = 0
    for path in iter_fs_images():
        try:
            size = os.path.getsize(path)
            if size > MAX_BYTES or size < MIN_BYTES:
                continue
            key = fs_key(path)
        except OSError:
            continue
        if cache.get(key):
            fs_skipped_cache += 1
            continue
        fs_items.append((fs_asset_id(path), os.path.basename(path), path, key))
    print(f"Filesystem: {len(fs_items)} new image(s), {fs_skipped_cache} unchanged (cached)")

    # --- gather Photos library images ---
    photos = collect_photos()
    photo_items = []  # (asset_id, filename, photo, cache_key)
    photo_skipped_cache = 0
    for p in photos:
        key = f"photo:{p.uuid}"
        if cache.get(key):
            photo_skipped_cache += 1
            continue
        photo_items.append((p.uuid, p.original_filename, p, key))
    print(f"Photos library: {len(photo_items)} new image(s), {photo_skipped_cache} cached, "
          f"({len(photos)} own photos total, Shared Album excluded)")

    # --- server-side pre-check by device_asset_id (skip already-stored) ---
    all_ids = [it[0] for it in fs_items] + [it[0] for it in photo_items]
    try:
        existing = check_existing(token, all_ids)
    except requests.HTTPError as e:
        print(f"  check_existing failed ({e.response.status_code}); relying on server dedup")
        existing = set()

    fs_items = [it for it in fs_items if it[0] not in existing]
    photo_items = [it for it in photo_items if it[0] not in existing]
    total = len(fs_items) + len(photo_items)
    if limit:
        fs_items = fs_items[:limit]
        photo_items = photo_items[:max(0, limit - len(fs_items))]
        total = len(fs_items) + len(photo_items)

    if dry_run:
        print(f"Dry run — {total} would upload")
        return

    tmp_root = tempfile.mkdtemp(prefix="akses_sync_")
    uploaded = saved = errors = 0
    n = 0
    try:
        # filesystem files
        for asset_id, filename, path, key in fs_items:
            n += 1
            sys.stdout.write(f"  [{n}/{total}] {filename}... "); sys.stdout.flush()
            try:
                r = upload_image(token, path, filename, asset_id)
                if r.status_code in (200, 201, 409):
                    cache[key] = True
                    uploaded += 1
                    if r.status_code == 201:
                        saved += 1
                    print("saved(NSFW)" if r.status_code == 201 else
                          ("exists" if r.status_code == 409 else "ok(not-nsfw)"))
                else:
                    errors += 1
                    print(f"FAIL {r.status_code}: {r.text[:60]}")
            except Exception as e:
                errors += 1
                print(f"ERROR: {e}")

        # Photos library (download missing originals on demand)
        for asset_id, filename, photo, key in photo_items:
            n += 1
            sys.stdout.write(f"  [{n}/{total}] {filename}... "); sys.stdout.flush()
            path, is_temp = None, False
            try:
                path, is_temp = ensure_local(photo, tmp_root)
                if not path:
                    errors += 1
                    print("SKIP (download failed)")
                    continue
                r = upload_image(token, path, filename, asset_id)
                if r.status_code in (200, 201, 409):
                    cache[key] = True
                    uploaded += 1
                    if r.status_code == 201:
                        saved += 1
                    print("saved(NSFW)" if r.status_code == 201 else
                          ("exists" if r.status_code == 409 else "ok(not-nsfw)"))
                else:
                    errors += 1
                    print(f"FAIL {r.status_code}: {r.text[:60]}")
            except Exception as e:
                errors += 1
                print(f"ERROR: {e}")
            finally:
                if is_temp and path and os.path.exists(path):
                    os.unlink(path)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
        save_cache(cache)

    print(f"\nDone: {uploaded} processed ({saved} NSFW saved), {errors} errors")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    limit = None
    for a in sys.argv:
        if a.startswith("--limit="):
            limit = int(a.split("=")[1])
    sync(dry_run=dry, limit=limit)
