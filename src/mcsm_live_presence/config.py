from pathlib import Path
import json
import os


def default_state_directory():
    return Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'mcsm-live-presence'


def config_path():
    selected = os.environ.get('MCSM_PRESENCE_CONFIG')
    if selected:
        return Path(selected).expanduser()
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'mcsm-live-presence/config.json'


def load_config(path=None):
    path = Path(path) if path else config_path()
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('Config must be a JSON object')
    app_id = str(data.get('discord_application_id', ''))
    if not app_id.isascii() or not app_id.isdigit() or not 15 <= len(app_id) <= 22:
        raise ValueError('Set discord_application_id to your Discord Application ID (not a token)')
    interval = float(data.get('poll_seconds', 2))
    if not 0.5 <= interval <= 30:
        raise ValueError('poll_seconds must be between 0.5 and 30')
    images = data.get('episode_image_keys', {})
    if not isinstance(images, dict) or any(not isinstance(v, str) for v in images.values()):
        raise ValueError('episode_image_keys must map episode numbers to asset keys')
    state = data.get('state_directory')
    if state and not isinstance(state, str):
        raise ValueError('state_directory must be a path string')
    data['state_directory'] = Path(state).expanduser().resolve() if state else default_state_directory().resolve()
    data['poll_seconds'] = interval
    data['discord_application_id'] = app_id
    return data
