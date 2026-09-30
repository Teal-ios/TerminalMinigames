"""Exercise the shared event loop with a deterministic terminal and frame clock."""
import unittest
from unittest.mock import Mock, patch

import arcade_screen


class InputLoopTests(unittest.TestCase):
    def loop(self, events):
        clock = [0.0]
        sleeps = []
        updates = []
        received = []
        window = Mock()
        window.getmaxyx.return_value = (40, 100)
        window.getch.side_effect = events
        game = Mock(over=False)
        game.handle.side_effect = received.append
        game.update.side_effect = lambda dt: updates.append(list(received))
        game.draw.side_effect = lambda screen: clock.__setitem__(0, clock[0] + .006)

        def sleep(delay):
            sleeps.append(delay)
            clock[0] += delay

        with patch.object(arcade_screen.sys.stdin, 'isatty', return_value=True), \
             patch.object(arcade_screen.sys.stdout, 'isatty', return_value=True), \
             patch.object(arcade_screen.curses, 'wrapper', side_effect=lambda fn: fn(window)), \
             patch.object(arcade_screen.curses, 'curs_set'), \
             patch.object(arcade_screen.curses, 'set_escdelay', create=True), \
             patch.object(arcade_screen, 'Screen'), \
             patch.object(arcade_screen.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(arcade_screen.time, 'sleep', side_effect=sleep):
            self.assertEqual(arcade_screen.run(lambda: game), 0)
        return updates, sleeps

    def test_queued_keys_reach_game_before_next_simulation_step(self):
        updates, _ = self.loop([10, ord('d'), ord('d'), ord('k'), -1, ord('q')])
        self.assertEqual(updates[0], [ord('d'), ord('d'), ord('k')])

    def test_render_time_is_part_of_frame_budget(self):
        _, sleeps = self.loop([10, -1, ord('q')])
        self.assertAlmostEqual(sleeps[0], 1/60 - .006)
