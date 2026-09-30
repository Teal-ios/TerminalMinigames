import random
import unittest

from games.fight.combat import FightGame
from games.fight.moves import BASIC, SWEEP, ROSTER


class BackGuardTests(unittest.TestCase):
    def arena(self, reversed_sides=False):
        game = FightGame(cpu_enabled=False, cpu_selected=0)
        game.start()
        game.fighters[0].x, game.fighters[1].x = (24, 20) if reversed_sides else (20, 24)
        game.boundaries()
        return game

    def test_back_direction_guards_on_either_side_of_opponent(self):
        for reversed_sides, back in ((False, 'a'), (True, 'd')):
            with self.subTest(back=back):
                game = self.arena(reversed_sides)
                game.press(0, back)
                self.assertEqual(game.connect(1, BASIC['k']), 'block')
                self.assertEqual(game.fighters[0].hp, 100)

    def test_guard_stops_low_special_and_former_guard_breaker_without_chip(self):
        for move in (SWEEP, ROSTER[0].skills['i'], ROSTER[0].skills['c']):
            with self.subTest(move=move.name):
                game = self.arena()
                game.press(0, 'a')
                self.assertEqual(game.connect(1, move), 'block')
                self.assertEqual(game.fighters[0].hp, 100)

    def test_grab_beats_standing_and_crouching_guard_and_can_be_broken(self):
        for crouched in (False, True):
            with self.subTest(crouched=crouched):
                game = self.arena()
                if crouched: game.press(0, 's')
                game.press(0, 'a')
                self.assertEqual(game.connect(1, BASIC['o']), 'hit')
                self.assertIsNotNone(game.throw)
                game.press(0, 'g')
                self.assertIsNone(game.throw)
                self.assertEqual(game.fighters[0].hp, 100)

    def test_forward_input_drops_guard_immediately(self):
        game = self.arena()
        game.press(0, 'a')
        game.press(0, 'd')
        self.assertEqual(game.connect(1, BASIC['k']), 'hit')

    def test_guard_interrupts_dash_instead_of_advancing_while_blocking(self):
        for defense in ('a', 'guard'):
            with self.subTest(defense=defense):
                game = self.arena()
                game.press(0, 'e')
                game.press(0, defense)
                game.update(.08)
                self.assertLessEqual(game.fighters[0].x, 20)
                self.assertEqual(game.fighters[0].dash, 0)

    def test_attack_and_airborne_states_cannot_back_guard(self):
        for action in ('j', 'w'):
            with self.subTest(action=action):
                game = self.arena()
                game.press(0, action)
                game.press(0, 'a')
                self.assertEqual(game.connect(1, BASIC['k']), 'hit')

    def test_back_guard_cannot_cancel_hitstun(self):
        game = self.arena()
        game.connect(1, BASIC['j'])
        game.press(0, 'a')
        self.assertEqual(game.connect(1, BASIC['j']), 'hit')

    def test_direction_guard_stops_when_sides_switch_or_input_expires(self):
        game = self.arena()
        game.press(0, 'a')
        self.assertGreater(game.fighters[0].guard, 0)
        game.fighters[0].x, game.fighters[1].x = 30, 26
        game.boundaries()
        self.assertEqual(game.connect(1, BASIC['k']), 'hit')
        game = self.arena()
        game.press(0, 'a')
        game.update(.5)
        self.assertEqual(game.fighters[0].guard, 0)

    def test_back_input_refreshes_guard_during_blockstun(self):
        game = self.arena()
        game.press(0, 'a')
        game.connect(1, BASIC['j'])
        game.fighters[0].guard = .01
        game.press(0, 'a')
        game.update(.05)
        self.assertGreater(game.fighters[0].guard, .15)

    def test_movement_bridges_short_key_repeat_gaps_then_stops(self):
        game = self.arena()
        game.fighters[1].x = 50
        game.press(0, 'd')
        game.update(.15)
        previous = game.fighters[0].x
        game.update(.05)
        self.assertGreater(game.fighters[0].x, previous)
        game.update(.5)
        previous = game.fighters[0].x
        game.update(.2)
        self.assertEqual(game.fighters[0].x, previous)

    def test_cpu_uses_throw_against_close_guard(self):
        for seed in range(10):
            with self.subTest(seed=seed):
                game = self.arena()
                game.rng = random.Random(seed)
                game.press(0, 'guard')
                game.cpu_action()
                self.assertIsNotNone(game.fighters[1].attack)
                self.assertEqual(game.fighters[1].attack.move.height, 'grab')
