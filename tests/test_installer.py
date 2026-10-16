from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
from mcsm_live_presence.installer import install, uninstall, NAMES


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.game, self.build = root / 'game', root / 'build'
        self.archives = self.game / 'archives'
        self.archives.mkdir(parents=True)
        (self.archives / 'MCSM_pc_Menu_data.ttarch2').write_bytes(b'synthetic original')
        (self.build / 'release').mkdir(parents=True)
        hashes = {}
        for name in NAMES:
            blob = ('synthetic ' + name).encode()
            (self.build / 'release' / name).write_bytes(blob)
            hashes[name] = hashlib.sha256(blob).hexdigest()
        (self.build / 'manifest.local.json').write_text(json.dumps({'format': 1, 'files': hashes}))
        mocked = patch('mcsm_live_presence.installer.require_closed_game')
        mocked.start()
        self.addCleanup(mocked.stop)

    def test_roundtrip_preserves_original(self):
        install(self.game, self.build)
        self.assertTrue(all((self.archives / name).exists() for name in NAMES))
        uninstall(self.game)
        self.assertFalse(any((self.archives / name).exists() for name in NAMES))
        self.assertEqual((self.archives / 'MCSM_pc_Menu_data.ttarch2').read_bytes(), b'synthetic original')

    def test_refuses_overwrite(self):
        name = sorted(NAMES)[0]
        (self.archives / name).write_bytes(b'existing')
        with self.assertRaises(RuntimeError):
            install(self.game, self.build)
        self.assertEqual((self.archives / name).read_bytes(), b'existing')
        self.assertFalse(any((self.archives / n).exists() for n in NAMES - {name}))

    def test_modified_file_prevents_all_uninstall_deletions(self):
        install(self.game, self.build)
        (self.archives / sorted(NAMES)[-1]).write_bytes(b'changed')
        with self.assertRaises(RuntimeError):
            uninstall(self.game)
        self.assertTrue(all((self.archives / name).exists() for name in NAMES))

    def test_bad_manifest_does_not_write(self):
        manifest = self.build / 'manifest.local.json'
        manifest.write_text(json.dumps({'format': 1, 'files': {'../unsafe': 'a' * 64}}))
        with self.assertRaises(ValueError):
            install(self.game, self.build)
        self.assertFalse(any((self.archives / name).exists() for name in NAMES))

    def test_bad_release_checksum_does_not_write(self):
        (self.build / 'release' / sorted(NAMES)[0]).write_bytes(b'changed')
        with self.assertRaises(RuntimeError):
            install(self.game, self.build)
        self.assertFalse(any((self.archives / name).exists() for name in NAMES))
