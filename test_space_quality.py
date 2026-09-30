"""Gameplay regressions for Star Defender's terminal controls and patterns."""
import unittest

from games.space.game import Enemy, SpaceGame, W, H


class RecordingScreen:
    width, height = 64, 32

    def __init__(self):
        self.calls = []
        self.positions = []

    def text(self, y, x, value, color=0):
        assert isinstance(x, int) and isinstance(y, int)
        assert 0 <= y < 32 and 0 <= x and x + len(str(value)) <= 64
        self.calls.append(str(value))
        self.positions.append((y, x, str(value)))

    def centered(self, y, value, color=0):
        self.text(y, (64 - len(value)) // 2, value, color)

    def border(self, y, height):
        assert y + height <= 32


class SpaceQualityTests(unittest.TestCase):
    def test_default_auto_fires_and_toggle_stops_it(self):
        game = SpaceGame()
        game.update(.6)
        self.assertGreater(len(game.shots), 0)
        game.handle(ord('f'))
        game.shots.clear()
        game.update(.4)
        self.assertEqual(game.shots, [])

    def test_input_bursts_do_not_teleport_and_motion_coasts_to_stop(self):
        game = SpaceGame()
        for _ in range(30):
            game.handle(ord('d'))
        self.assertEqual(game.x, 30)
        game.update(.1)
        self.assertGreater(game.x, 30)
        self.assertLess(game.x, 32)
        game.update(1)
        stopped = game.x
        game.update(.3)
        self.assertAlmostEqual(game.x, stopped)

    def test_motion_clamps_whole_ship_inside_arena(self):
        game = SpaceGame()
        for _ in range(40):
            game.handle(ord('d'))
            game.handle(ord('s'))
            game.update(.1)
        self.assertLessEqual(game.x, W - 2)
        self.assertLessEqual(game.y, H - 1)
        screen = RecordingScreen()
        game.draw(screen)

    def test_engine_trail_does_not_draw_over_lower_border(self):
        game = SpaceGame()
        game.y = 20.9
        screen = RecordingScreen()
        game.draw(screen)
        self.assertFalse(any(y == 26 for y, _, _ in screen.positions))

    def test_swept_shot_hits_nearest_enemy_instead_of_list_order(self):
        game = SpaceGame()
        game.auto = False
        near, far = Enemy(20, 15, 10), Enemy(20, 9, 10)
        game.enemies = [near, far]
        game.shots = [(20, 18)]
        game.update(.5)
        self.assertNotIn(near, game.enemies)
        self.assertIn(far, game.enemies)
        self.assertEqual(game.score, 100)

    def test_weaver_moves_sideways_and_armour_needs_three_hits(self):
        game = SpaceGame()
        game.auto = False
        weaver = Enemy(10, 3, 10, kind='weaver')
        armour = Enemy(40, 7, 10, kind='gunship')
        game.enemies = [weaver, armour]
        game.update(.3)
        self.assertNotEqual(weaver.x, 10)
        for remaining in (2, 1, 0):
            game.shots = [(armour.x, armour.y + .3)]
            game.update(.01)
            self.assertEqual(armour.hp, remaining)
        self.assertNotIn(armour, game.enemies)
        self.assertGreater(game.score, 100)
        self.assertTrue(game.effects)

    def test_regular_fire_warns_before_firing_and_escapes_are_survivable(self):
        game = SpaceGame()
        game.auto = False
        scout = Enemy(10, 3, 0)
        game.enemies = [scout]
        game.update(.1)
        self.assertEqual(game.hostile, [])
        self.assertGreater(scout.warning, 0)
        game.update(.6)
        self.assertTrue(game.hostile)
        game.enemies = [Enemy(50, H - .01, 10)]
        game.update(.1)
        self.assertEqual(game.lives, 3)

    def test_fourth_wave_boss_warns_lanes_before_firing(self):
        game = SpaceGame()
        game.auto = False
        game.start_wave(4)
        game.update(2)
        boss = next(enemy for enemy in game.enemies if enemy.kind == 'boss')
        self.assertGreater(boss.hp, 10)
        boss.cooldown = 0
        game.hostile.clear()
        game.update(.1)
        self.assertEqual(game.hostile, [])
        self.assertGreater(boss.warning, 0)
        locked_lanes = list(boss.lanes)
        game.x = 2
        game.update(.8)
        self.assertEqual([x for x, _ in game.hostile], locked_lanes)
        screen = RecordingScreen()
        game.draw(screen)
        self.assertTrue(any('BOSS' in line for line in screen.calls))

    def test_bomb_is_limited_clears_fire_and_cannot_instant_kill_boss(self):
        game = SpaceGame()
        boss = Enemy(30, 3, 10, kind='boss')
        game.enemies = [boss, Enemy(20, 5, 10)]
        game.hostile = [(game.x, game.y)]
        hp = boss.hp
        game.handle(ord('x'))
        self.assertEqual(game.hostile, [])
        self.assertEqual(game.enemies, [boss])
        self.assertLess(boss.hp, hp)
        self.assertGreater(boss.hp, 0)
        self.assertGreater(game.invincible, 0)
        game.handle(ord('x'))
        hp = boss.hp
        game.handle(ord('x'))
        self.assertEqual(boss.hp, hp)
        self.assertEqual(game.bombs, 0)

    def test_large_step_and_small_steps_agree_for_shots_and_damage(self):
        games = [SpaceGame(), SpaceGame()]
        for game in games:
            game.auto = False
            game.hostile = [(30, 14)] * 3
            game.enemies = [Enemy(15, 6, 10)]
            game.shots = [(15, 18)]
        games[0].update(1)
        for _ in range(100):
            games[1].update(.01)
        self.assertEqual(games[0].score, games[1].score)
        self.assertEqual(games[0].lives, games[1].lives)
        self.assertEqual(games[0].lives, 2)

    def test_wave_progression_and_boss_reward(self):
        game = SpaceGame()
        game.auto = False
        game.start_wave(1)
        seen = set()
        for _ in range(150):
            game.update(.05)
            seen.update(enemy.kind for enemy in game.enemies)
            game.enemies.clear()
            if game.wave > 1:
                break
        self.assertEqual(seen, {'scout', 'weaver', 'gunship'})
        self.assertEqual(game.wave, 2)
        game.start_wave(4)
        game.update(1.5)
        boss = next(enemy for enemy in game.enemies if enemy.kind == 'boss')
        boss.hp = 1
        game.bombs = 0
        game.shots = [(boss.x, boss.y + .3)]
        game.update(.01)
        self.assertNotIn(boss, game.enemies)
        self.assertEqual(game.bombs, 1)
        self.assertGreaterEqual(game.score, 1500)


if __name__ == '__main__':
    unittest.main()
