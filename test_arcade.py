import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from arcade_cli import discover, launch


class PluginTests(unittest.TestCase):
    def make_plugin(self, root, name='demo', entry='game.py'):
        folder = root / name
        folder.mkdir()
        (folder / 'game.json').write_text(json.dumps({
            'id': name, 'name': 'Demo', 'description': 'Example game',
            'entry': entry,
        }))
        (folder / 'game.py').write_text('raise SystemExit(7)\n')
        return folder

    def test_new_plugin_is_discovered_without_launcher_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_plugin(root)
            plugins, errors = discover(root)
            self.assertEqual(list(plugins), ['demo'])
            self.assertEqual(errors, [])
            self.assertEqual(launch(plugins['demo']), 7)

    def test_bad_plugin_does_not_hide_working_games(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_plugin(root)
            broken = root / 'broken'
            broken.mkdir()
            (broken / 'game.json').write_text('{broken')
            plugins, errors = discover(root)
            self.assertIn('demo', plugins)
            self.assertEqual(len(errors), 1)

    def test_entry_cannot_escape_plugin_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'outside.py').write_text('raise SystemExit(0)')
            self.make_plugin(root, entry='../outside.py')
            plugins, errors = discover(root)
            self.assertEqual(plugins, {})
            self.assertEqual(len(errors), 1)

    def test_cli_lists_games_from_another_working_directory(self):
        cli = Path(__file__).parent / 'arcade'
        result = subprocess.run([sys.executable, str(cli), 'list'],
                                cwd='/tmp', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('poop', result.stdout)

    def test_unknown_game_exits_with_helpful_error(self):
        cli = Path(__file__).parent / 'arcade'
        result = subprocess.run([sys.executable, str(cli), 'missing'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('arcade list', result.stderr)


if __name__ == '__main__':
    unittest.main()
