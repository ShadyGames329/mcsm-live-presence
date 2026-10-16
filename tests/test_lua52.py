import unittest
from mcsm_live_presence.lua52 import Prototype, abc, mark_episode_menu, u32


class MarkerTests(unittest.TestCase):
    def prototype(self):
        def string(value):
            return b'\x04' + u32(len(value) + 1) + value + b'\0'
        code = [abc(5, 0, 0, 0), abc(29, 0, 1, 1), abc(6, 0, 0, 256),
                abc(6, 1, 0, 256), 1 | (2 << 6) | (1 << 14),
                abc(5, 3, 0, 0), abc(29, 0, 4, 2), abc(31, 0, 1, 0)]
        tail = u32(0) + u32(0) + u32(0) + u32(0) + u32(0)
        return Prototype(bytes(10) + b'\x08', code,
                         [string(b'Menu_Create'), string(b'ui_episodeSelect')], [], tail, [], 0)

    def test_marks_only_verified_creation_result(self):
        proto = self.prototype()
        original = proto.code[:]
        mark_episode_menu(proto)
        self.assertEqual(proto.code[:7] + proto.code[8:], original)
        instruction = proto.code[7]
        self.assertEqual(instruction & 63, 10)
        self.assertEqual((instruction >> 6) & 255, 0)
        key = ((instruction >> 23) & 511) - 256
        value = ((instruction >> 14) & 511) - 256
        self.assertEqual(proto.string(key), b'__MCSM_episodeBrowser')
        self.assertEqual(proto.constants[value], b'\x01\x01')

    def test_rejects_different_creation_call(self):
        proto = self.prototype()
        proto.code[6] = abc(29, 1, 4, 2)
        with self.assertRaises(ValueError):
            mark_episode_menu(proto)

    def test_rejects_jump_crossing_insertion(self):
        proto = self.prototype()
        proto.code.append(23 | ((131071 - 9) << 14))  # pc8 -> pc0
        with self.assertRaises(ValueError):
            mark_episode_menu(proto)

    def test_updates_debug_line_table(self):
        import struct
        proto = self.prototype()
        count = len(proto.code)
        proto.tail = u32(0) + u32(0) + u32(count) + b''.join(u32(n) for n in range(count)) + u32(0) + u32(0)
        mark_episode_menu(proto)
        self.assertEqual(struct.unpack_from('<I', proto.tail, 8)[0], count + 1)
        lines = struct.unpack_from('<' + 'I' * (count + 1), proto.tail, 12)
        self.assertEqual(lines, tuple(range(7)) + (7, 7))

    def test_updates_debug_local_ranges(self):
        import struct
        proto = self.prototype()
        proto.tail = u32(0) + u32(0) + u32(0) + u32(1) + u32(2) + b'x\0' + u32(1) + u32(8) + u32(0)
        mark_episode_menu(proto)
        self.assertEqual(struct.unpack_from('<II', proto.tail, 22), (1, 9))


if __name__ == '__main__':
    unittest.main()
