import random
import unittest

from games.breakout.game import Ball, Brick, BreakoutGame, Item


class BreakoutTests(unittest.TestCase):
    def active_game(self):
        game = BreakoutGame(rng=random.Random(1))
        game.launched = True
        return game

    def test_brick_hit_scores_reflects_and_can_drop_item(self):
        game = self.active_game()
        game.bricks = [Brick(10, 5), Brick(30, 5)]
        game.balls = [Ball(12, 6, 0, -12)]
        game.update(0.05)
        self.assertEqual(len(game.bricks), 1)
        self.assertEqual(game.score, 10)
        self.assertGreater(game.balls[0].vy, 0)
        self.assertEqual(len(game.items), 1)
        self.assertIn(game.items[0].kind, ('double', 'wide', 'slow', 'life'))

    def test_brick_side_hit_reflects_horizontally(self):
        game = self.active_game()
        game.bricks = [Brick(10, 5), Brick(30, 5)]
        game.balls = [Ball(9, 5, 12, 0)]
        game.update(0.05)
        self.assertLess(game.balls[0].vx, 0)
        self.assertEqual(game.score, 10)

    def test_paddle_edge_aims_ball_to_that_side(self):
        game = self.active_game()
        game.balls = [Ball(game.paddle + 3, 19.3, 0, 12)]
        game.update(0.05)
        self.assertLess(game.balls[0].vy, 0)
        self.assertGreater(game.balls[0].vx, 0)

    def test_one_lost_ball_does_not_cost_life_while_another_survives(self):
        game = self.active_game()
        game.balls = [Ball(0, 21.9, 0, 12), Ball(30, 12, 3, -12)]
        game.update(0.05)
        self.assertEqual(game.lives, 3)
        self.assertEqual(len(game.balls), 1)

    def test_losing_all_balls_costs_one_life_and_waits_for_serve(self):
        game = self.active_game()
        game.balls = [Ball(0, 21.9, 0, 12), Ball(59, 21.9, 0, 12)]
        game.update(0.05)
        self.assertEqual(game.lives, 2)
        self.assertFalse(game.launched)
        self.assertEqual(len(game.balls), 1)
        game.update(1)
        self.assertEqual(game.lives, 2)

    def test_catching_double_item_doubles_balls_with_distinct_directions(self):
        game = self.active_game()
        game.balls = [Ball(30, 12, 3, -12), Ball(20, 12, -3, -12)]
        game.items = [Item(game.paddle, 19.9, 'double')]
        game.update(0.05)
        self.assertEqual(len(game.balls), 4)
        self.assertEqual(len({(round(b.vx, 2), round(b.vy, 2)) for b in game.balls}), 4)
        for _ in range(5):
            game.apply_item('double')
        self.assertEqual(len(game.balls), 8)

    def test_missed_item_does_not_activate(self):
        game = self.active_game()
        game.items = [Item(0, 21.9, 'life')]
        game.update(0.05)
        self.assertEqual(game.lives, 3)
        self.assertEqual(game.items, [])

    def test_wide_and_slow_expire_without_compounding_velocity(self):
        game = self.active_game()
        original_width = game.paddle_width
        game.balls = [Ball(30, 12, 6, 0)]
        game.apply_item('wide')
        game.apply_item('slow')
        self.assertGreater(game.paddle_width, original_width)
        game.update(0.1)
        self.assertAlmostEqual(game.balls[0].x, 30.39)
        self.assertEqual(game.balls[0].vx, 6)
        game.wide_timer = game.slow_timer = 0.01
        game.update(0.02)
        self.assertEqual(game.paddle_width, original_width)
        self.assertEqual(game.slow_timer, 0)

    def test_last_brick_wins_and_last_life_loses(self):
        game = self.active_game()
        game.stage = 3
        game.bricks = [Brick(10, 5)]
        game.balls = [Ball(12, 6, 0, -12)]
        game.update(0.05)
        self.assertTrue(game.over)
        self.assertIn('CLEAR', game.result)
        game = self.active_game()
        game.lives = 1
        game.balls = [Ball(0, 21.9, 0, 12)]
        game.update(0.05)
        self.assertTrue(game.over)
        self.assertEqual(game.lives, 0)


if __name__ == '__main__':
    unittest.main()
