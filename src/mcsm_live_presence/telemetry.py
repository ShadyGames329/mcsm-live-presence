"""Read the game probe's small event file; reject earlier sessions and partial writes."""
from pathlib import Path


def telemetry_mode(event: dict, latest_gameplay_write_ns: int) -> str:
    mode = {'menu': 'menu', 'browsing': 'browsing', 'paused': 'paused', 'gameplay': 'game'}.get(event['mode'], 'unknown')
    if mode == 'menu' and latest_gameplay_write_ns > event['_modified_ns']:
        return 'unknown'
    return mode


def read_telemetry(path: Path, session_started_ns: int) -> dict | None:
    try:
        with path.open('rb') as handle:
            import os
            before = os.fstat(handle.fileno())
            if before.st_mtime_ns < session_started_ns or not 0 < before.st_size <= 4096:
                return None
            data = handle.read(4097)
            after = os.fstat(handle.fileno())
        if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
            return None
        if len(data) != after.st_size or not data.endswith(b'\n'):
            return None
        fields = {}
        for line in data.decode('utf-8').splitlines():
            key, value = line.split('=', 1)
            if key in fields:
                return None
            fields[key] = value
        required = {'format', 'mode', 'presence_key', 'event_count'}
        metadata = {'episode', 'chapter', 'scene', 'script', 'metadata_source'}
        if fields.get('format') == '2':
            required |= metadata
        if set(fields) != required:
            return None
        if fields['format'] not in ('1', '2') or not fields['event_count'].isascii() or not fields['event_count'].isdigit():
            return None
        if not 0 < int(fields['event_count']) < 2**53:
            return None
        mode, key = fields['mode'], fields['presence_key']
        valid = ((mode == 'menu' and key == 'richPresence_mainMenu')
                 or (fields['format'] == '2' and mode == 'browsing' and key == 'richPresence_mainMenu')
                 or (mode == 'paused' and key == 'richPresence_pauseMenu')
                 or (mode == 'gameplay' and (key.startswith('richPresence_episode') or key == 'restored_from_pause'))
                 or (mode == 'unknown' and key == 'probe_initialized'))
        if valid:
            if fields['format'] == '2':
                import re
                if fields['episode'] and fields['episode'] not in tuple(str(n) for n in range(1, 9)):
                    return None
                if fields['metadata_source'] not in ('', 'live_scene', 'live_script'):
                    return None
                for field in ('chapter', 'scene', 'script'):
                    if len(fields[field]) > 160 or (fields[field] and not re.fullmatch(r'[A-Za-z0-9_. /-]+', fields[field])):
                        return None
            fields['_modified_ns'] = after.st_mtime_ns
            return fields
        return None
    except (OSError, UnicodeError, ValueError):
        return None
