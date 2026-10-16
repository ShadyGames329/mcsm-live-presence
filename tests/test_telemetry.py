from pathlib import Path
import tempfile
import unittest
from mcsm_live_presence.telemetry import read_telemetry


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / 'live-state.txt'

    def event(self, mode='menu', key='richPresence_mainMenu', episode=''):
        return (f'format=2\nmode={mode}\npresence_key={key}\nepisode={episode}\n'
                'chapter=\nscene=\nscript=\nmetadata_source=\nevent_count=2\n')

    def test_current_and_prior_sessions(self):
        self.file.write_text(self.event())
        stamp = self.file.stat().st_mtime_ns
        self.assertEqual(read_telemetry(self.file, stamp)['mode'], 'menu')
        self.assertIsNone(read_telemetry(self.file, stamp + 1))

    def test_browser(self):
        self.file.write_text(self.event('browsing'))
        self.assertEqual(read_telemetry(self.file, 0)['mode'], 'browsing')

    def test_rejects_partial_duplicate_malformed_and_oversized(self):
        for content in [self.event()[:-1], self.event() + 'mode=paused\n',
                        self.event('paused'), self.event(episode='99'), 'x' * 4097]:
            self.file.write_text(content)
            self.assertIsNone(read_telemetry(self.file, 0))

    def test_missing(self):
        self.assertIsNone(read_telemetry(self.file, 0))
