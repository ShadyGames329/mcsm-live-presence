"""Small lossless reader for the already-inspected game Lua 5.2 chunk layout."""
from dataclasses import dataclass
import struct


def u32(value):
    return struct.pack('<I', value)


@dataclass
class Prototype:
    header: bytes
    code: list
    constants: list
    children: list
    tail: bytes
    bindings: list
    env_index: int | None = None

    def encode(self):
        return (self.header + u32(len(self.code))
                + b''.join(u32(x) for x in self.code)
                + u32(len(self.constants)) + b''.join(self.constants)
                + u32(len(self.children)) + b''.join(c.encode() for c in self.children)
                + self.tail)

    def string(self, index):
        raw = self.constants[index]
        return raw[5:-1] if raw[:1] == b'\x04' else None

    def add_string(self, value):
        for index in range(len(self.constants)):
            if self.string(index) == value:
                return index
        self.constants.append(b'\x04' + u32(len(value) + 1) + value + b'\0')
        return len(self.constants) - 1

    def insert_instructions(self, index, instructions):
        """Keep optional line tables aligned with inserted instructions."""
        pos = 4 + 2 * len(self.bindings)
        source_size = struct.unpack_from('<I', self.tail, pos)[0]
        pos += 4 + source_size
        count = struct.unpack_from('<I', self.tail, pos)[0]
        if count not in (0, len(self.code)):
            raise ValueError('Unexpected debug line table length')
        debug_end = pos + 4 + count * 4
        remaining = bytearray(self.tail[debug_end:])
        local_count = struct.unpack_from('<I', remaining, 0)[0]
        local_pos = 4
        for _ in range(local_count):
            name_size = struct.unpack_from('<I', remaining, local_pos)[0]
            local_pos += 4 + name_size
            start, end = struct.unpack_from('<II', remaining, local_pos)
            start += len(instructions) if start >= index else 0
            end += len(instructions) if end >= index else 0
            struct.pack_into('<II', remaining, local_pos, start, end)
            local_pos += 8
        if count:
            lines = list(struct.unpack_from('<' + 'I' * count, self.tail, pos + 4))
            line = lines[min(index, count - 1)]
            updated = lines[:index] + [line] * len(instructions) + lines[index:]
            self.tail = (self.tail[:pos] + u32(len(updated))
                         + b''.join(u32(x) for x in updated) + remaining)
        else:
            self.tail = self.tail[:debug_end] + remaining
        self.code[index:index] = instructions


def parse_chunk(data):
    expected = bytes.fromhex('520001040404040019930d0a1a0a')
    if not data.startswith(expected):
        raise ValueError('Unsupported Lua header')
    pos = len(expected)

    def take(n):
        nonlocal pos
        if n < 0 or pos + n > len(data):
            raise ValueError('Truncated chunk')
        value = data[pos:pos+n]; pos += n
        return value

    def count():
        n = struct.unpack('<I', take(4))[0]
        if n > len(data):
            raise ValueError('Invalid count')
        return n

    def string():
        raw = take(count())
        if raw and not raw.endswith(b'\0'):
            raise ValueError('Invalid string')

    def function():
        header = take(11)
        code = [struct.unpack('<I', take(4))[0] for _ in range(count())]
        constants = []
        for _ in range(count()):
            start = pos
            tag = take(1)[0]
            if tag == 4:
                string()
            elif tag == 3:
                take(4)
            elif tag == 1:
                take(1)
            elif tag != 0:
                raise ValueError('Unknown constant tag')
            constants.append(data[start:pos])
        children = [function() for _ in range(count())]
        tail_start = pos
        bindings = [tuple(take(2)) for _ in range(count())]
        string()  # source
        take(count() * 4)  # lines
        for _ in range(count()):
            string(); take(8)
        for _ in range(count()):
            string()
        return Prototype(header, code, constants, children, data[tail_start:pos], bindings)

    root = function()
    if pos != len(data) or expected + root.encode() != data:
        raise ValueError('Chunk did not round-trip')
    root.env_index = 0

    def assign_env(parent):
        for child in parent.children:
            matches = [i for i, (stack, index) in enumerate(child.bindings)
                       if stack == 0 and index == parent.env_index]
            child.env_index = matches[0] if len(matches) == 1 else None
            assign_env(child)
    assign_env(root)
    return expected, root


def abc(op, a, b, c):
    return op | a << 6 | c << 14 | b << 23


def find_global_function(root, name):
    found = []
    for index, instruction in enumerate(root.code[:-1]):
        if instruction & 63 != 37:  # CLOSURE
            continue
        register, child = (instruction >> 6) & 255, instruction >> 14
        following = root.code[index + 1]
        op, a = following & 63, (following >> 6) & 255
        b, c = (following >> 23) & 511, (following >> 14) & 511
        if (op == 8 and a == root.env_index and c == register and b >= 256
                and root.string(b - 256) == name):
            found.append(root.children[child])
    if len(found) != 1:
        raise ValueError(f'Expected unique global function {name!r}, got {len(found)}')
    return found[0]


def notify_at_entry(prototype, callback):
    if prototype.env_index is None:
        raise ValueError('Function environment upvalue not established')
    scratch = prototype.header[10]
    if scratch + 3 > 255:
        raise ValueError('No scratch registers')
    call_index = prototype.add_string(b'pcall')
    callback_index = prototype.add_string(callback)
    if max(call_index, callback_index) >= 256:
        raise ValueError('Constant cannot be used as RK operand')
    prefix = [abc(6, scratch, prototype.env_index, call_index + 256),
              abc(6, scratch + 1, prototype.env_index, callback_index + 256),
              abc(0, scratch + 2, 0, 0),  # MOVE original menu argument
              abc(29, scratch, 3, 1)]
    original = prototype.code[:]
    prototype.insert_instructions(0, prefix)
    prototype.header = prototype.header[:10] + bytes([scratch + 3])
    assert prototype.code[4:] == original


def mark_episode_menu(prototype):
    """Tag only the object returned by the verified episode Menu_Create call."""
    code = prototype.code
    if len(code) < 7:
        raise ValueError('Unexpected episode constructor')
    # Verified original: R0 = Menu_Create(Menu, "ui_episodeSelect", class).
    create, resource, invoke = code[2], code[4], code[6]
    if not (create & 63 == 6 and (create >> 6) & 255 == 0
            and (create >> 23) & 511 == prototype.env_index
            and (create >> 14) & 511 >= 256
            and prototype.string(((create >> 14) & 511) - 256) == b'Menu_Create'
            and resource & 63 == 1 and (resource >> 6) & 255 == 2
            and prototype.string(resource >> 14) == b'ui_episodeSelect'
            and invoke == abc(29, 0, 4, 2)):
        raise ValueError('Episode menu creation differs from inspected input')
    insertion = 7
    # Reject any relative jump crossing the insertion rather than guessing offsets.
    for pc, instruction in enumerate(code):
        if instruction & 63 in (23, 32, 33, 35):
            target = pc + 1 + (instruction >> 14) - 131071
            if (pc < insertion <= target) or (target < insertion <= pc):
                raise ValueError('Jump crosses private-marker insertion')
    key = prototype.add_string(b'__MCSM_episodeBrowser')
    true_raw = b'\x01\x01'
    if true_raw not in prototype.constants:
        prototype.constants.append(true_raw)
    value = prototype.constants.index(true_raw)
    if max(key, value) >= 256:
        raise ValueError('Marker constant exceeds RK range')
    original = code[:]
    prototype.insert_instructions(insertion, [abc(10, 0, key + 256, value + 256)])
    assert prototype.code[:insertion] + prototype.code[insertion+1:] == original
