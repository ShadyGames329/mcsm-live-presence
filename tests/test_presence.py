import unittest
from mcsm_live_presence.presence import make_payload


class PresenceTests(unittest.TestCase):
    def payload(self, **event):
        return make_payload(event, start=123, config={'large_image_key': 'cover'})

    def test_screen_states(self):
        for mode, label in [('menu', 'Main Menu'), ('browsing', 'Browsing Episodes'), ('paused', 'Paused')]:
            self.assertEqual(self.payload(mode=mode)['details'], label)

    def test_live_episode_and_scene(self):
        result = self.payload(mode='gameplay', episode='1', chapter='', scene='ForestTreehouse')
        self.assertEqual(result['details'], 'Episode 1: The Order of the Stone')
        self.assertEqual(result['state'], 'Forest Treehouse')

    def test_chapter_is_optional_and_must_match_episode(self):
        result = self.payload(mode='gameplay', episode='1', chapter='101_chapter2', scene='Wilderness')
        self.assertEqual(result['state'], 'Chapter 2 | Wilderness')
        result = self.payload(mode='gameplay', episode='1', chapter='108_chapter2', scene='Wilderness')
        self.assertEqual(result['state'], 'Wilderness')

    def test_no_progress_is_invented(self):
        result = self.payload(mode='gameplay')
        self.assertEqual(result['details'], 'Playing')
        for mode in ('menu', 'paused', 'browsing', 'unknown', 'gameplay'):
            result = self.payload(mode=mode)
            self.assertNotIn('slot', str(result).lower())
            self.assertNotIn('last save', str(result).lower())

    def test_scene_privacy_and_length(self):
        result = make_payload({'mode': 'gameplay', 'episode': '1', 'scene': 'PrivateScene'},
                              start=0, config={'show_scene': False})
        self.assertNotIn('Private', result['state'])
        self.assertLessEqual(len(self.payload(mode='gameplay', scene='x' * 200)['state']), 128)
