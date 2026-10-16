"""Build game-derived sidecars locally. No original assets are distributed."""
from importlib.resources import files
from pathlib import Path
import hashlib
import json

from .config import default_state_directory
from .lua52 import abc, parse_chunk, find_global_function, notify_at_entry, mark_episode_menu


def inject_loader(root, module):
    if not root.code or root.code[-1] != abc(31, 0, 1, 0):
        raise ValueError('Unexpected root return; refusing to patch')
    scratch = root.header[10]
    if scratch + 3 > 255:
        raise ValueError('No scratch registers for module loader')
    pcall = root.add_string(b'pcall')
    require = root.add_string(b'require')
    name = root.add_string(module.encode('ascii'))
    if max(pcall, require) >= 256:
        raise ValueError('Unsupported constant count')
    additions = [abc(6, scratch, root.env_index, pcall + 256),
                 abc(6, scratch + 1, root.env_index, require + 256),
                 1 | ((scratch + 2) << 6) | (name << 14),
                 abc(29, scratch, 3, 1)]
    original = root.code[:]
    root.insert_instructions(len(root.code) - 1, additions)
    root.header = root.header[:10] + bytes([scratch + 3])
    assert root.code[:-5] == original[:-1]


def archives_directory(game_dir):
    root = Path(game_dir).expanduser().resolve()
    candidates = [root] if root.name.lower() == 'archives' else [root / 'archives', root / 'Archives']
    for candidate in candidates:
        if (candidate / 'MCSM_pc_Menu_data.ttarch2').is_file():
            return candidate
    raise ValueError('Season One PC archives were not found at --game-dir')


def lua_path(value):
    if any(ord(c) < 32 for c in value):
        raise ValueError('Telemetry path contains control characters')
    return json.dumps(value, ensure_ascii=False)


def build_mod(game_dir, output, state_dir=None, windows_state_dir=None, diagnostics=False):
    try:
        from ttg_cli_inspector.ttarch2 import Ttarch2Archive
        from ttg_cli_inspector.patches import decrypt_lenc, encrypt_lenc, build_sidecar_patch
    except ImportError as exc:
        raise RuntimeError('Install the optional build dependency: pip install -e ".[mod]"') from exc
    archives = archives_directory(game_dir)
    output = Path(output).expanduser().resolve()
    state = Path(state_dir).expanduser().resolve() if state_dir else default_state_directory().resolve()
    if output.exists():
        raise ValueError('Build output already exists; use a fresh output directory')
    if output == archives or archives in output.parents:
        raise ValueError('Build into a separate directory, outside game archives')
    if state == archives or archives in state.parents:
        raise ValueError('Telemetry state must be outside game archives')
    windows = (windows_state_dir or ('Z:' + state.as_posix())).rstrip('/\\')
    if not (len(windows) >= 3 and windows[1] == ':' and windows[2] in '/\\'):
        raise ValueError('--windows-state-dir must be an absolute Windows path')
    state.mkdir(parents=True, exist_ok=True)
    release = output / 'release'
    hashes, input_hashes = {}, {}
    for destination, archive_name, stem, module, resource in [
        ('Project', 'MCSM_pc_Project_data.ttarch2', 'LivePresence_Project', 'MCSM_LiveProbe.lua', 'live_probe.lua'),
        ('Menu', 'MCSM_pc_Menu_data.ttarch2', 'LivePresence_Menu', 'MCSM_MenuObserver.lua', 'menu_observer.lua'),
    ]:
        archive = Ttarch2Archive(archives / archive_name)
        stage = output / 'staging' / destination
        stage.mkdir(parents=True)
        scripts = ['RichPresence.lua'] if destination == 'Project' else ['Menu.lua', 'Menu_EpisodeSelect.lua']
        for script in scripts:
            matches = [entry for entry in archive.files if entry.name == script]
            if len(matches) != 1:
                raise ValueError(f'Missing or duplicate original script: {script}')
            original = archive.read_file(matches[0])
            if original[:4] != b'\x1bLEn':
                raise ValueError(f'Unsupported original script container: {script}')
            plain = decrypt_lenc(b'\x1bLEo' + original[4:], 'mcsm-season-one')
            header, root = parse_chunk(plain)
            if script == 'Menu.lua':
                notify_at_entry(find_global_function(root, b'Menu_Show'), b'MCSM_MenuObserved')
            elif script == 'Menu_EpisodeSelect.lua':
                mark_episode_menu(find_global_function(root, b'Menu_EpisodeSelect'))
            if script != 'Menu_EpisodeSelect.lua':
                inject_loader(root, module)
            patched = header + root.encode()
            parse_chunk(patched)
            encoded = b'\x1bLEn' + encrypt_lenc(patched, 'mcsm-season-one')[4:]
            if decrypt_lenc(b'\x1bLEo' + encoded[4:], 'mcsm-season-one') != patched:
                raise RuntimeError('Modified script encryption verification failed')
            (stage / script).write_bytes(encoded)
            input_hashes[script] = hashlib.sha256(original).hexdigest()
        source = files('mcsm_live_presence').joinpath('lua', resource).read_text(encoding='utf-8')
        source = (source.replace('__TELEMETRY_PATH__', lua_path(windows + '/live-state.txt'))
                  .replace('__OBSERVER_LOG_PATH__', lua_path(windows + '/menu-observer.txt'))
                  .replace('__DIAGNOSTICS_ENABLED__', 'true' if diagnostics else 'false'))
        encoded = encrypt_lenc(source.encode('utf-8'), 'mcsm-season-one')
        if decrypt_lenc(encoded, 'mcsm-season-one') != source.encode('utf-8'):
            raise RuntimeError('Probe source encryption verification failed')
        (stage / module).write_bytes(encoded)
        result = build_sidecar_patch(stage, release, name=stem, destination=destination,
                                     priority=1100, enable_mode='constant', profile='mcsm-season-one')
        for key in ('archive', 'descriptor'):
            path = Path(result[key])
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {'format': 1, 'files': hashes, 'inputs': input_hashes}
    (output / 'manifest.local.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return {'release_directory': str(release), 'state_directory': str(state),
            'files': sorted(hashes), 'installed': False}
