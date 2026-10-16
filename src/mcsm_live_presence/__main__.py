import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Live Discord presence for Minecraft: Story Mode')
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('run', help='Run the Discord companion')
    run.add_argument('--config', type=Path)
    build = commands.add_parser('build', help='Build sidecars locally from your own game files')
    build.add_argument('--game-dir', type=Path, required=True)
    build.add_argument('--output', type=Path, default=Path('build/mod'))
    build.add_argument('--state-dir', type=Path)
    build.add_argument('--windows-state-dir', help='Override the Proton Z: mapping for telemetry')
    build.add_argument('--diagnostics', action='store_true')
    for action in ('install', 'uninstall'):
        command = commands.add_parser(action, help=f'{action.title()} only manifest-listed sidecars')
        command.add_argument('--game-dir', type=Path, required=True)
        command.add_argument('--build-dir', type=Path, default=Path('build/mod'))
    commands.add_parser('status', help='Print current telemetry, without connecting to Discord').add_argument('--config', type=Path)
    preview = commands.add_parser('preview', help='Preview sample presence text without Discord')
    preview.add_argument('mode', choices=['menu', 'browsing', 'gameplay', 'paused'])
    args = parser.parse_args()
    try:
        if args.command == 'run':
            from .companion import run
            return run(args.config)
        if args.command == 'build':
            from .mod import build_mod
            print(json.dumps(build_mod(args.game_dir, args.output, args.state_dir,
                                       args.windows_state_dir, args.diagnostics), indent=2))
        elif args.command in ('install', 'uninstall'):
            from .installer import install, uninstall
            (install if args.command == 'install' else uninstall)(args.game_dir, args.build_dir)
            print(f'{args.command.title()} complete; original archives were not modified.')
        elif args.command == 'status':
            from .config import load_config
            from .telemetry import read_telemetry
            state = load_config(args.config)['state_directory']
            print(json.dumps(read_telemetry(state / 'live-state.txt', 0), indent=2))
        elif args.command == 'preview':
            from .presence import make_payload
            event = {'format': '2', 'mode': args.mode, 'episode': '1',
                     'chapter': '', 'scene': 'Wilderness'}
            print(json.dumps(make_payload(event, start=0, config={}), indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
