import unittest

from games.space.game import SpaceGame, Enemy
from games.volley.game import VolleyGame


class SpaceTests(unittest.TestCase):
    def test_shot_destroys_enemy_and_scores(self):
        game = SpaceGame()
        game.enemies = [Enemy(20, 8, 10)]
        game.shots = [(20, 8.5)]
        game.update(0.05)
        self.assertEqual(game.score, 100)
        self.assertEqual(game.enemies, [])
        self.assertEqual(game.shots, [])

    def test_hit_costs_one_life_then_grants_invulnerability(self):
        game = SpaceGame()
        game.hostile = [(game.x, game.y - 0.1)] * 3
        game.update(0.05)
        self.assertEqual(game.lives, 2)
        game.invincible = 0
        game.lives = 1
        game.hostile = [(game.x, game.y - 0.1)]
        game.update(0.05)
        self.assertTrue(game.over)

    def test_fire_has_cooldown(self):
        game = SpaceGame()
        game.fire()
        game.fire()
        self.assertEqual(len(game.shots), 1)
        game.update(0.3)
        game.fire()
        self.assertEqual(len(game.shots), 2)


class VolleyTests(unittest.TestCase):
    def test_ball_on_player_ground_scores_for_cpu(self):
        game = VolleyGame()
        game.serving = 0
        game.ball = [5.0, 0.6, 0.0, -5.0]
        game.update(0.05)
        self.assertEqual(game.scores, [0, 1])
        self.assertGreater(game.serving, 0)

    def test_fifth_point_finishes_match(self):
        game = VolleyGame()
        game.scores = [4, 0]
        game.serving = 0
        game.ball = [59.0, 0.6, 0.0, -5.0]
        game.update(0.05)
        self.assertEqual(game.scores, [5, 0])
        self.assertTrue(game.over)
        self.assertIn('WIN', game.result)

    def test_net_blocks_low_ball(self):
        game = VolleyGame()
        game.serving = 0
        game.ball = [29.0, 5.0, 12.0, 0.0]
        game.update(0.05)
        self.assertLess(game.ball[2], 0)
        self.assertLess(game.ball[0], 30)

    def test_jump_returns_to_ground(self):
        game = VolleyGame()
        game.jump(0)
        game.update(0.05)
        self.assertGreater(game.players[0][1], 0)
        for _ in range(25):
            game.update(0.05)
        self.assertEqual(game.players[0][1], 0)

    def test_descending_ball_bounces_on_player(self):
        game = VolleyGame()
        game.serving = 0
        game.ball = [game.players[0][0], 4.0, 0.0, -5.0]
        game.update(0.05)
        self.assertGreater(game.ball[3], 0)
        self.assertGreater(game.ball[2], 0)


if __name__ == '__main__':
    unittest.main()
