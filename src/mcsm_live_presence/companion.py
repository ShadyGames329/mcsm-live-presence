import logging
import os
import signal
import time

from .config import load_config
from .presence import make_payload
from .telemetry import read_telemetry

LOG = logging.getLogger('mcsm-live-presence')


def run(config_file=None):
    from pypresence import Presence
    config = load_config(config_file)
    state = config['state_directory']
    state.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.FileHandler(state / 'presence.log'), logging.StreamHandler()])
    started_ns = int(os.environ.get('MCSM_PRESENCE_SESSION_NS', time.time_ns()))
    start = started_ns // 1_000_000_000
    stopping, rpc, previous = False, None, None

    def stop(_signal, _frame):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    LOG.info('Started live presence; no save files are read')
    try:
        while not stopping:
            try:
                event = read_telemetry(state / 'live-state.txt', started_ns)
                payload = make_payload(event, start=start, config=config)
                if rpc is None:
                    rpc = Presence(config['discord_application_id'])
                    rpc.connect()
                    previous = None
                    LOG.info('Connected to Discord IPC')
                if payload != previous:
                    rpc.update(**payload)
                    previous = payload
                    LOG.info('Updated presence: %s | %s', payload['details'], payload['state'])
            except Exception as exc:
                LOG.warning('Presence unavailable; retrying: %s', exc)
                if rpc:
                    try:
                        rpc.close()
                    except Exception:
                        pass
                rpc, previous = None, None
            deadline = time.monotonic() + config['poll_seconds']
            while not stopping and time.monotonic() < deadline:
                time.sleep(min(0.25, max(0, deadline - time.monotonic())))
    finally:
        if rpc:
            try:
                rpc.clear()
            except Exception:
                pass
            finally:
                try:
                    rpc.close()
                except Exception:
                    pass
        LOG.info('Stopped live presence')
    return 0
