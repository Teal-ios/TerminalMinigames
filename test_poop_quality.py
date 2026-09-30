import random
import unittest

from games.poop.game import Drop, Game


class PoopQualityTests(unittest.TestCase):
    def game(self):
        return Game(rng=random.Random(5))

    def test_warning_precedes_hazard(self):
        game = self.game()
        game.update(.7)
        self.assertTrue(game.warnings)
        self.assertFalse(game.drops)
        game.update(.7)
        self.assertTrue(game.drops)

    def test_move_is_time_based_and_expires(self):
        game = self.game()
        before = game.player
        game.move(1)
        self.assertEqual(game.player, before)
        game.update(.1)
        self.assertGreater(game.player, before)
        game.update(.6)
        stopped = game.player
        game.update(.1)
        self.assertEqual(game.player, stopped)

    def test_dash_has_cooldown_and_cannot_be_extended(self):
        game = self.game()
        game.move(-1)
        game.handle(ord(' '))
        self.assertGreater(game.dash_timer, 0)
        game.update(.08)
        remaining = game.dash_timer
        game.handle(ord(' '))
        self.assertEqual(game.dash_timer, remaining)
        self.assertGreater(game.dash_cooldown, 0)

    def test_repeated_damage_has_invulnerability_and_third_hit_ends_run(self):
        game = self.game()
        game.hurt()
        game.hurt()
        self.assertEqual(game.lives, 2)
        self.assertFalse(game.over)
        game.invincible = 0
        game.hurt()
        game.invincible = 0
        game.hurt()
        self.assertTrue(game.over)

    def test_restart_preserves_best_but_resets_gameplay(self):
        game = self.game()
        game.elapsed = 22
        game.hurt()
        restarted = game.restart()
        self.assertEqual(restarted.best, game.score)
        self.assertEqual(restarted.lives, 3)
        self.assertEqual(restarted.elapsed, 0)

    def test_collision_uses_player_position_when_drop_crosses_ground(self):
        game = self.game()
        game.player, game.vx = 30, 22
        game.move(1)
        game.drops = [Drop(29.4, 20.99, 16)]
        game.update(.02)
        self.assertEqual(game.lives, 2)
        self.assertEqual(game.near_misses, 0)

    def test_lethal_hit_does_not_award_later_near_miss_points(self):
        game = self.game()
        game.lives = 1
        game.drops = [Drop(30, 20.9, 10), Drop(35, 20.9, 10)]
        game.update(.02)
        self.assertEqual(game.score, 0)
        self.assertIn(f'SCORE {game.score}', game.result)

    def test_near_miss_is_awarded_only_once(self):
        game = self.game()
        game.drops = [Drop(31.5, 20.9, 10)]
        game.update(.02)
        self.assertEqual(game.near_misses, 1)
        self.assertEqual(game.bonus, 30)
        game.update(.1)
        self.assertEqual(game.near_misses, 1)
