from pathlib import Path
import json
import tempfile
import unittest
from mcsm_live_presence.config import load_config


class ConfigTests(unittest.TestCase):
    def test_invalid_ids_and_intervals(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.json'
            for data in ({'discord_application_id': 'token'},
                         {'discord_application_id': '123456789012345678', 'poll_seconds': 0}):
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    load_config(path)

    def test_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.json'
            path.write_text(json.dumps({'discord_application_id': '123456789012345678',
                                        'state_directory': tmp}))
            self.assertEqual(load_config(path)['state_directory'], Path(tmp).resolve())
