import random
import unittest

from games.fight.combat import FightGame
from games.fight.moves import BASIC


class FightQualityTests(unittest.TestCase):
    def arena(self, distance=5):
        game = FightGame(rng=random.Random(1), cpu_enabled=False, cpu_selected=0)
        game.start()
        game.fighters[0].x, game.fighters[1].x = 20, 20 + distance
        return game

    def test_attack_can_connect_after_startup_while_hitbox_is_active(self):
        game = self.arena(9)
        game.press(0, 'j')
        game.update(0.10)
        game.fighters[1].x = 25
        game.update(0.02)
        self.assertLess(game.fighters[1].hp, 100)

    def test_expired_active_window_does_not_gain_an_extra_collision_tick(self):
        game = self.arena(9)
        game.press(0, 'j')
        game.update(0.175)
        game.fighters[1].x = 25
        game.update(0.02)
        self.assertEqual(game.fighters[1].hp, 100)

    def test_hitbox_cannot_hit_someone_behind_attacker(self):
        game = self.arena()
        game.fighters[1].x = 15
        game.connect(0, BASIC['j'])
        self.assertEqual(game.fighters[1].hp, 100)

    def test_hitstop_freezes_physics_and_clock_but_buffers_next_attack(self):
        game = self.arena(4)
        game.press(0, 'j')
        game.update(0.085)
        self.assertGreater(game.hitstop, 0)
        time_left = game.remaining
        attack_time = game.fighters[0].attack.elapsed
        game.press(0, 'k')
        game.update(0.01)
        self.assertEqual(game.remaining, time_left)
        self.assertEqual(game.fighters[0].attack.elapsed, attack_time)
        self.assertEqual(len(game.fighters[0].queue), 1)

    def test_hit_produces_contact_spark_and_floating_damage(self):
        game = self.arena()
        game.connect(0, BASIC['j'])
        self.assertIn('hit', [effect.kind for effect in game.effects])
        self.assertIn('damage', [effect.kind for effect in game.effects])

    def test_counter_hit_interrupts_startup_and_is_stronger(self):
        normal = self.arena(4)
        normal.connect(0, BASIC['j'])
        counter = self.arena(4)
        counter.press(1, 'k')
        counter.connect(0, BASIC['j'])
        self.assertLess(counter.fighters[1].hp, normal.fighters[1].hp)
        self.assertIsNone(counter.fighters[1].attack)
        self.assertIn('COUNTER', counter.message)

    def test_walk_moves_over_time_instead_of_teleporting(self):
        game = self.arena(15)
        game.press(0, 'd')
        self.assertEqual(game.fighters[0].x, 20)
        game.update(0.05)
        self.assertGreater(game.fighters[0].x, 20)
        self.assertLess(game.fighters[0].x, 22)

    def test_guard_spark_does_not_turn_into_repeated_damage(self):
        game = self.arena()
        game.press(1, 'guard')
        game.press(0, 'j')
        game.update(0.3)
        self.assertEqual(game.fighters[1].hp, 100)
        self.assertEqual(game.fighters[0].meter, 3)

    def test_effects_expire_and_round_reset_clears_them(self):
        game = self.arena()
        game.connect(0, BASIC['j'])
        game.update(2)
        self.assertEqual(game.effects, [])
        game.connect(0, BASIC['j'])
        game.new_round()
        self.assertEqual(game.effects, [])
        self.assertEqual(game.hitstop, 0)
