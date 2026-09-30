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
    def test_ground_space_slides_in_last_move_direction_without_jumping(self):
        game = VolleyGame()
        game.handle(ord('a'))
        x = game.players[0][0]
        game.handle(ord(' '))
        game.update(0.1)
        self.assertLess(game.players[0][0], x - 2)
        self.assertEqual(game.players[0][1], 0)
        self.assertEqual(game.smash, 0)
        self.assertGreater(game.slide_timer[0], 0)

    def test_airborne_space_spikes_without_starting_slide(self):
        game = VolleyGame()
        game.handle(ord('w'))
        game.handle(ord(' '))
        self.assertGreater(game.smash, 0)
        self.assertEqual(game.slide_timer[0], 0)
        game.update(0.05)
        self.assertGreater(game.players[0][1], 0)

    def test_slide_has_recovery_and_cannot_be_extended_by_repeated_space(self):
        game = VolleyGame()
        game.handle(ord(' '))
        game.update(0.1)
        remaining = game.slide_timer[0]
        game.handle(ord(' '))
        game.handle(ord('w'))
        self.assertEqual(game.slide_timer[0], remaining)
        self.assertEqual(game.players[0][2], 0)
        for _ in range(6):
            game.update(0.05)
        self.assertEqual(game.slide_timer[0], 0)
        self.assertGreater(game.recovery[0], 0)
        x = game.players[0][0]
        game.handle(ord('a'))
        self.assertEqual(game.players[0][0], x)
        for _ in range(5):
            game.update(0.05)
        game.handle(ord('w'))
        self.assertGreater(game.players[0][2], 0)

    def test_slide_receives_a_low_ball_that_standing_player_misses(self):
        for sliding in (False, True):
            game = VolleyGame()
            game.serving = 0
            if sliding:
                game.handle(ord(' '))
            game.ball = [game.players[0][0] + 1, 1.4, 0, -4]
            game.update(0.05)
            if sliding:
                self.assertGreater(game.ball[3], 0)
            else:
                self.assertLess(game.ball[3], 0)

    def test_slide_stays_in_court_and_serve_resets_motion(self):
        game = VolleyGame()
        game.players[0][0] = 25
        game.handle(ord(' '))
        game.update(0.2)
        self.assertLessEqual(game.players[0][0], 26)
        game.serve(0)
        self.assertEqual(game.slide_timer, [0, 0])
        self.assertEqual(game.recovery, [0, 0])

    def test_slide_cannot_receive_ball_through_the_net(self):
        game = VolleyGame()
        game.serving = 0
        game.players[0][0] = 26
        game.handle(ord(' '))
        game.ball = [31, 1.5, 0, -3]
        game.update(0.01)
        self.assertLess(game.ball[3], 0)

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
