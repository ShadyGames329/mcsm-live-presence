"""Check the Git index for local/proprietary artifacts before publication."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SUFFIXES = {'.ttarch2', '.landb', '.bundle', '.estore', '.epage', '.prop',
                      '.exe', '.dll', '.zip', '.bak', '.luac', '.pyc', '.log'}


def main():
    raw = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, check=True, capture_output=True).stdout
    paths = [Path(value.decode()) for value in raw.split(b'\0') if value]
    if not paths:
        raise SystemExit('No tracked files to audit')
    errors = []
    patterns = [re.compile(rb'/home/[A-Za-z0-9_.-]+/'),
                re.compile(rb'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----'),
                re.compile(rb'(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}')]
    for relative in paths:
        path = ROOT / relative
        if (relative.suffix.lower() in FORBIDDEN_SUFFIXES or relative.name in ('config.json', '.env')
                or relative.name.endswith('.local.json')
                or any(part in ('build', 'state', 'telemetry', '.venv', '__pycache__') for part in relative.parts)):
            errors.append(f'Excluded artifact is tracked: {relative}')
            continue
        if path.is_symlink():
            errors.append(f'Unexpected symlink: {relative}')
            continue
        data = path.read_bytes()
        if data.startswith((b'\x1bLua', b'\x1bLEn', b'\x1bLEo', b'NCTT', b'ZCTT')) or b'\0' in data:
            errors.append(f'Binary/game-derived file: {relative}')
        if any(pattern.search(data) for pattern in patterns):
            errors.append(f'Potential credential or machine-specific path: {relative}')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'Publication audit passed: {len(paths)} source/documentation files; no excluded artifacts detected.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
