"""Discover local game plugins and run each in its own process."""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


@dataclass
class Plugin:
    id: str
    name: str
    description: str
    entry: Path


def discover(directory):
    plugins, errors = {}, []
    for manifest in sorted(Path(directory).glob('*/game.json')):
        try:
            data = json.loads(manifest.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                raise ValueError('game.json must be an object')
            for field in ('id', 'name', 'description', 'entry'):
                if not isinstance(data.get(field), str) or not data[field].strip():
                    raise ValueError(f'missing or invalid {field}')
            if not re.fullmatch(r'[a-z][a-z0-9-]*', data['id']):
                raise ValueError('invalid game id')
            if data['id'] in plugins or data['id'] == 'list':
                raise ValueError('duplicate or reserved game id')
            entry = (manifest.parent / data['entry']).resolve()
            if manifest.parent.resolve() not in entry.parents:
                raise ValueError('entry must be inside its plugin folder')
            if not entry.is_file() or entry.suffix != '.py':
                raise ValueError('entry must be an existing Python file')
            plugins[data['id']] = Plugin(data['id'], data['name'], data['description'], entry)
        except (OSError, ValueError) as error:
            errors.append(f'{manifest.parent.name}: {error}')
    return plugins, errors


def launch(plugin):
    try:
        return subprocess.call([sys.executable, str(plugin.entry)], cwd=plugin.entry.parent)
    except KeyboardInterrupt:
        return 130


def main():
    parser = argparse.ArgumentParser(description='터미널 미니 오락실')
    parser.add_argument('game', nargs='?', help='게임 ID 또는 list (생략하면 선택 메뉴)')
    args = parser.parse_args()
    plugins, errors = discover(ROOT / 'games')
    for error in errors:
        print(f'플러그인 건너뜀: {error}', file=sys.stderr)
    if args.game and args.game != 'list':
        if args.game not in plugins:
            print(f'알 수 없는 게임: {args.game}. arcade list로 목록을 확인하세요.', file=sys.stderr)
            return 2
        return launch(plugins[args.game])
    print('\n🎮 TERMINAL ARCADE\n')
    ordered = list(plugins.values())
    for number, plugin in enumerate(ordered, 1):
        print(f'  {number}. {plugin.name}  [{plugin.id}]\n     {plugin.description}')
    if args.game == 'list':
        return 0
    if not ordered:
        print('games 폴더에 게임 플러그인을 추가하세요.')
        return 1
    if not sys.stdin.isatty():
        print('\n실행: arcade <게임 ID>')
        return 0
    while True:
        try:
            choice = input('\n게임 번호 / ID (Q: 종료): ').strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if choice in ('q', 'quit'):
            return 0
        if choice.isdigit() and 1 <= int(choice) <= len(ordered):
            return launch(ordered[int(choice) - 1])
        if choice in plugins:
            return launch(plugins[choice])
        print('목록에 있는 번호 또는 ID를 입력하세요.')


if __name__ == '__main__':
    raise SystemExit(main())
