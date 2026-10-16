"""Manifest-scoped installer with checksum checks, exclusive writes and rollback."""
from pathlib import Path
import hashlib
import json
import os

from .mod import archives_directory

NAMES = {f'MCSM_pc_LivePresence_{kind}.ttarch2' for kind in ('Project', 'Menu')} | {
    f'_resdesc_50_LivePresence_{kind}.lua' for kind in ('Project', 'Menu')}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require_closed_game():
    proc = Path('/proc')
    if not proc.is_dir():
        raise RuntimeError('This installer currently supports Linux only')
    for process in proc.iterdir():
        if not process.name.isdigit():
            continue
        try:
            name = (process / 'comm').read_text().strip().lower()
        except OSError:
            continue
        if 'minecraft' in name or 'storymode' in name:
            raise RuntimeError('Close Minecraft: Story Mode before changing diagnostic files')


def read_manifest(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('format') != 1 or not isinstance(data.get('files'), dict) or set(data['files']) != NAMES:
        raise ValueError('Unexpected manifest contents; no files changed')
    if any(not isinstance(v, str) or len(v) != 64 or any(c not in '0123456789abcdef' for c in v)
           for v in data['files'].values()):
        raise ValueError('Invalid manifest hash')
    return data


def install(game_dir, build_dir):
    require_closed_game()
    archives = archives_directory(game_dir)
    build = Path(build_dir).expanduser().resolve()
    record = archives / '.mcsm-live-presence-installed.local.json'
    if record.exists():
        raise RuntimeError('An installation record exists; uninstall that version first')
    if any('LiveState' in p.name for p in archives.iterdir()):
        raise RuntimeError('Remove earlier LiveState experimental sidecars using their original manifests first')
    data = read_manifest(build / 'manifest.local.json')
    content = {}
    for name, digest in data['files'].items():
        source, target = build / 'release' / name, archives / name
        if source.is_symlink() or target.exists() or target.is_symlink():
            raise RuntimeError(f'Unsafe source or destination already exists: {name}')
        content[name] = source.read_bytes()
        if sha(content[name]) != digest:
            raise RuntimeError(f'Release checksum mismatch: {name}')
    created = []
    try:
        for name, blob in content.items():
            target = archives / name
            with target.open('xb') as handle:
                created.append(target)
                handle.write(blob)
                handle.flush()
                os.fsync(handle.fileno())
            if sha(target.read_bytes()) != data['files'][name]:
                raise RuntimeError(f'Installed checksum mismatch: {name}')
        with record.open('x', encoding='utf-8') as handle:
            created.append(record)
            json.dump(data, handle, indent=2)
            handle.write('\n')
    except BaseException:
        for target in reversed(created):
            target.unlink(missing_ok=True)
        raise


def uninstall(game_dir, build_dir=None):
    require_closed_game()
    archives = archives_directory(game_dir)
    record = archives / '.mcsm-live-presence-installed.local.json'
    if record.is_symlink():
        raise RuntimeError('Installation record is a symlink; no files changed')
    data = read_manifest(record)
    # Check every file before removing any. Never delete an unknown/modified file.
    for name, digest in data['files'].items():
        target = archives / name
        if target.is_symlink() or not target.is_file() or sha(target.read_bytes()) != digest:
            raise RuntimeError(f'Installed file missing or changed: {name}; no files removed')
    for name in data['files']:
        (archives / name).unlink()
    record.unlink()
