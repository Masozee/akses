"""Standalone Windows installer and sync launcher."""
import argparse
import contextlib
from datetime import datetime
import os
from pathlib import Path
import runpy
import subprocess
import sys
import traceback


def main():
    parser = argparse.ArgumentParser(description='Akses Sync for Windows. Run without arguments to install.')
    parser.add_argument('--version', action='version', version='Akses Sync 1.0.0')
    parser.add_argument('--sync', action='store_true', help='Run the configured backup')
    parser.add_argument('--dry-run', action='store_true', help='Preview without uploading images')
    parser.add_argument('--limit', type=int, help='Maximum images to upload')
    parser.add_argument('--self-test', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    bundle = Path(__file__).resolve().parent
    if args.self_test:
        import requests
        import certifi
        assert Path(certifi.where()).is_file()
        for name in ('sync.py', 'install.ps1', 'uninstall.ps1'):
            assert (bundle / name).is_file(), name
        compile((bundle / 'sync.py').read_text(encoding='utf-8'), 'sync.py', 'exec')
        print('Bundled engine, installer, requests and TLS certificates: OK')
        return 0
    if sys.platform != 'win32':
        parser.error('This executable requires Windows.')
    if not args.sync:
        if args.dry_run or args.limit is not None:
            parser.error('Use --sync with --dry-run or --limit.')
        if not getattr(sys, 'frozen', False):
            parser.error('Use install.ps1 for a source installation.')
        # Restore DLL lookup before starting a system program from a frozen app.
        import ctypes
        ctypes.windll.kernel32.SetDllDirectoryW(None)
        powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        result = subprocess.run([str(powershell), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                                 str(bundle / 'install.ps1'), '-PackageExecutable', sys.executable])
        input('Press Enter to close...')
        return result.returncode
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be positive.')
    root = Path(os.environ['LOCALAPPDATA']) / 'akses-sync'
    if not (root / 'config.json').is_file():
        parser.error('Run AksesSync.exe without arguments to configure this computer first.')
    sys.argv = ['sync.py']
    if args.dry_run:
        sys.argv.append('--dry-run')
    if args.limit is not None:
        sys.argv.append(f'--limit={args.limit}')
    print(f'Sync log: {root / "sync.log"}')
    with (root / 'sync.log').open('a', encoding='utf-8', buffering=1) as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            print(f'=== {datetime.now().isoformat()} sync start ===')
            try:
                runpy.run_path(str(bundle / 'sync.py'), run_name='__main__')
            except Exception:
                traceback.print_exc()
                return 1
            finally:
                print(f'=== {datetime.now().isoformat()} sync end ===')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
