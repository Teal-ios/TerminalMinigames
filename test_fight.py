import random
import unittest

from games.fight.combat import FightGame


class FightTests(unittest.TestCase):
    def arena(self, distance=5):
        game = FightGame(rng=random.Random(7), cpu_enabled=False)
        game.start()
        game.fighters[0].x = 25
        game.fighters[1].x = 25 + distance
        return game

    def advance(self, game, seconds):
        for _ in range(round(seconds / 0.01)):
            game.update(0.01)

    def test_attack_has_startup_and_hits_only_once(self):
        game = self.arena()
        hp = game.fighters[1].hp
        game.press(0, 'j')
        self.advance(game, 0.03)
        self.assertEqual(game.fighters[1].hp, hp)
        self.advance(game, 0.16)
        self.assertLess(game.fighters[1].hp, hp)
        damaged = game.fighters[1].hp
        self.advance(game, 0.5)
        self.assertEqual(game.fighters[1].hp, damaged)

    def test_attack_out_of_range_whiffs(self):
        game = self.arena(distance=15)
        hp = game.fighters[1].hp
        game.press(0, 'j')
        self.advance(game, 0.5)
        self.assertEqual(game.fighters[1].hp, hp)

    def test_standing_guard_blocks_mid_but_sweep_beats_it(self):
        game = self.arena()
        defender = game.fighters[1]
        game.press(1, 'guard')
        game.press(0, 'k')
        self.advance(game, 0.4)
        self.assertEqual(defender.hp, defender.profile.hp)
        self.advance(game, 0.5)
        game.press(1, 'guard')
        game.press(0, 's')
        game.press(0, 'l')
        self.advance(game, 0.4)
        self.assertLess(defender.hp, defender.profile.hp)

    def test_crouch_guard_blocks_low_and_ducks_jab(self):
        game = self.arena()
        defender = game.fighters[1]
        game.press(1, 's')
        game.press(1, 'guard')
        game.press(0, 's')
        game.press(0, 'l')
        self.advance(game, 0.4)
        self.assertEqual(defender.hp, defender.profile.hp)

    def test_buffered_jjk_becomes_three_hit_combo(self):
        game = self.arena(distance=4)
        for key in 'jjk':
            game.press(0, key)
        self.advance(game, 0.8)
        attacker = game.fighters[0]
        self.assertGreaterEqual(attacker.combo_hits, 3)
        self.assertEqual(attacker.last_move, 'RUSH FINISH')

    def test_launcher_lifts_opponent_for_followup(self):
        game = self.arena(distance=4)
        game.press(0, 'u')
        self.advance(game, 0.35)
        self.assertGreater(game.fighters[1].y, 0)
        self.assertGreater(game.fighters[1].vy, 0)
        hp = game.fighters[1].hp
        game.press(0, 'l')
        self.advance(game, 0.2)
        self.assertLess(game.fighters[1].hp, hp)

    def test_grab_ignores_guard_and_can_be_broken(self):
        game = self.arena(distance=4)
        defender = game.fighters[1]
        game.press(1, 'guard')
        game.press(0, 'o')
        self.advance(game, 0.2)
        self.assertIsNotNone(game.throw)
        game.press(1, 'g')
        self.advance(game, 0.5)
        self.assertIsNone(game.throw)
        self.assertEqual(defender.hp, defender.profile.hp)

    def test_unbroken_throw_deals_damage_and_knocks_down(self):
        game = self.arena(distance=4)
        game.press(0, 'o')
        self.advance(game, 0.55)
        self.assertLess(game.fighters[1].hp, game.fighters[1].profile.hp)
        self.assertGreater(game.fighters[1].down, 0)

    def test_crouching_opponent_avoids_grab(self):
        game = self.arena(distance=4)
        game.press(1, 's')
        game.press(0, 'o')
        self.advance(game, 0.25)
        self.assertIsNone(game.throw)

    def test_skill_and_super_require_meter(self):
        game = self.arena(distance=6)
        attacker = game.fighters[0]
        game.press(0, 'i')
        self.advance(game, 0.1)
        self.assertIsNone(attacker.attack)
        attacker.meter = 100
        game.press(0, 'h')
        self.advance(game, 0.1)
        self.assertEqual(attacker.meter, 0)
        self.assertIsNotNone(attacker.attack)

    def test_stunned_player_cannot_attack(self):
        game = self.arena()
        game.fighters[0].stun = 1
        game.press(0, 'j')
        self.advance(game, 0.3)
        self.assertIsNone(game.fighters[0].attack)

    def test_two_round_wins_finish_match(self):
        game = self.arena()
        game.fighters[1].hp = 0
        game.update(0.01)
        self.assertEqual(game.wins, [1, 0])
        self.assertFalse(game.over)
        self.advance(game, 2)
        self.assertEqual(game.fighters[1].hp, game.fighters[1].profile.hp)
        game.fighters[1].hp = 0
        game.update(0.01)
        self.assertTrue(game.over)
        self.assertIn('YOU WIN', game.result)

    def test_timeout_uses_remaining_health_percentage(self):
        game = self.arena()
        game.remaining = 0.01
        game.fighters[1].hp = 10
        game.update(0.02)
        self.assertEqual(game.wins, [1, 0])

    def test_roster_choice_is_preserved_on_restart(self):
        game = FightGame()
        game.handle_menu(ord('3'))
        game.start()
        restarted = game.restart()
        self.assertEqual(restarted.selected, 2)
        self.assertEqual(restarted.fighters[0].profile.name, 'IRON')

    def test_cpu_can_be_selected_independently_and_survives_restart(self):
        for key, name in [('4', 'STRIKER'), ('5', 'RUSH'), ('6', 'IRON')]:
            game = FightGame()
            game.handle_menu(ord('2'))
            game.handle_menu(ord(key))
            game.start()
            self.assertEqual(game.fighters[0].profile.name, 'RUSH')
            self.assertEqual(game.fighters[1].profile.name, name)
            restarted = game.restart()
            restarted.start()
            self.assertEqual(restarted.fighters[1].profile.name, name)

    def test_random_cpu_varies_between_matches_but_not_between_rounds(self):
        opponents = set()
        for seed in range(12):
            game = FightGame(rng=random.Random(seed))
            game.handle_menu(ord('5'))
            game.handle_menu(ord('0'))
            game.start()
            self.assertIsNone(game.cpu_selected)
            name = game.fighters[1].profile.name
            opponents.add(name)
            game.new_round()
            self.assertEqual(game.fighters[1].profile.name, name)
        self.assertEqual(opponents, {'STRIKER', 'RUSH', 'IRON'})

    def test_all_fifteen_unique_skills_execute_and_damage(self):
        names = set()
        for selection in range(3):
            for key in 'izxch':
                with self.subTest(character=selection, key=key):
                    game = FightGame(selection, cpu_enabled=False, cpu_selected=0)
                    game.start()
                    attacker, defender = game.fighters
                    attacker.x, defender.x = 20, 24
                    attacker.meter = 100
                    defender.hp = 300
                    if key == 'x':
                        defender.x = 40
                    game.press(0, key)
                    self.advance(game, 1.5)
                    self.assertLess(defender.hp, 300)
                    self.assertLess(attacker.meter, 100)
                    names.add(attacker.last_move)
        self.assertEqual(len(names), 15)

    def test_high_jab_misses_crouching_opponent(self):
        game = self.arena()
        game.press(1, 's')
        game.press(0, 'j')
        self.advance(game, 0.2)
        self.assertEqual(game.fighters[1].hp, game.fighters[1].profile.hp)

    def test_mid_attack_beats_low_guard(self):
        game = self.arena()
        game.press(1, 's')
        game.press(1, 'guard')
        game.press(0, 'k')
        self.advance(game, 0.3)
        self.assertLess(game.fighters[1].hp, game.fighters[1].profile.hp)

    def test_expired_input_cannot_trigger_a_late_combo_finisher(self):
        game = self.arena(distance=15)
        game.press(0, 'j')
        self.advance(game, 0.5)
        game.press(0, 'j')
        self.advance(game, 1.5)
        game.press(0, 'k')
        self.assertEqual(game.fighters[0].last_move, 'HEAVY')

    def test_six_hit_cap_forces_knockdown(self):
        from games.fight.moves import BASIC
        game = self.arena(distance=4)
        game.fighters[1].hp = 500
        for _ in range(6):
            game.connect(0, BASIC['j'])
        self.assertEqual(game.fighters[0].combo_hits, 6)
        self.assertGreater(game.fighters[1].down, 0)
        hp = game.fighters[1].hp
        game.connect(0, BASIC['j'])
        self.assertEqual(game.fighters[1].hp, hp)

    def test_iron_armor_takes_damage_without_losing_its_attack(self):
        game = FightGame(selected=0, cpu_selected=2, cpu_enabled=False)
        game.start()
        game.fighters[0].x, game.fighters[1].x = 25, 29
        game.fighters[1].meter = 100
        game.press(1, 'i')
        game.press(0, 'j')
        self.advance(game, 0.15)
        self.assertIsNotNone(game.fighters[1].attack)
        self.assertLess(game.fighters[1].hp, 120)

    def test_jump_avoids_low_projectile(self):
        game = FightGame(selected=2, cpu_selected=0, cpu_enabled=False)
        game.start()
        game.fighters[0].x, game.fighters[1].x = 20, 27
        game.fighters[0].meter = 100
        game.press(0, 'x')
        self.advance(game, 0.25)
        game.press(1, 'w')
        self.advance(game, 0.6)
        self.assertEqual(game.fighters[1].hp, 100)


if __name__ == '__main__':
    unittest.main()
