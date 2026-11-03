"""Offline regression checks: no account access or image uploads."""
import json
import os
from pathlib import Path
import runpy
import tempfile
import types
import unittest
from unittest.mock import patch

ENGINE = Path(__file__).resolve().parents[1] / 'Sync-dist/Sync.app/Contents/Resources/sync.py'


class PlatformTests(unittest.TestCase):
    def load_engine(self, folder, platform):
        home = Path(folder)
        support = home / ('akses-sync' if platform == 'win32' else 'Library/Application Support/akses-sync')
        support.mkdir(parents=True)
        images = home / 'Pictures with spaces'
        images.mkdir()
        nested = images / 'nested'
        nested.mkdir()
        (images / 'photo.JPG').write_bytes(b'x' * 60000)
        (nested / 'image.png').write_bytes(b'y' * 60000)
        (images / 'notes.txt').write_text('not an image')
        config = dict(base_url='https://example.invalid', email='test', password='test', scan_dirs=[str(images), str(nested)])
        # Windows PowerShell 5.1 writes a BOM when using Set-Content -Encoding UTF8.
        (support / 'config.json').write_text(json.dumps(config), encoding='utf-8-sig')
        session = types.SimpleNamespace(headers={})
        fake_requests = types.SimpleNamespace(Session=lambda: session)
        with patch('pathlib.Path.home', return_value=home), patch('sys.platform', platform), patch.dict(os.environ, {'LOCALAPPDATA': folder}), patch.dict('sys.modules', {'requests': fake_requests}):
            return runpy.run_path(str(ENGINE)), support, images

    def test_windows_scan_deduplicates_overlapping_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine, support, images = self.load_engine(tmp, 'win32')
            paths = list(engine['iter_fs_images']())
            self.assertEqual(set(paths), {str(images / 'photo.JPG'), str(images / 'nested/image.png')})
            self.assertEqual(len(paths), 2)
            self.assertEqual(engine['collect_photos'](), [])
            self.assertEqual(engine['CACHE_FILE'], support / 'cache.json')
            engine['save_cache']({'sample': True})
            self.assertEqual(engine['load_cache'](), {'sample': True})

    def test_mac_paths_and_scan_roots_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine, support, _ = self.load_engine(tmp, 'darwin')
            self.assertEqual(engine['CONFIG_FILE'], support / 'config.json')
            self.assertEqual(engine['CACHE_FILE'], Path(tmp) / '.akses_sync_cache.json')
            self.assertIn(Path(tmp) / 'Library/Messages/Attachments', engine['SCAN_DIRS'])
            self.assertTrue(engine['SCAN_GLOBS'])


if __name__ == '__main__':
    unittest.main()
