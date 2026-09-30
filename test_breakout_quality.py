"""Physics, stages and responsive controls for Brick Burst."""
import math
import random
import unittest

from games.breakout.game import Ball, Brick, BreakoutGame


class BreakoutQualityTests(unittest.TestCase):
    def arena(self):
        game = BreakoutGame(rng=random.Random(8))
        game.launched = True
        game.bricks = [Brick(1, 2)]
        return game

    def test_direction_input_moves_over_time_and_stops_after_repeat_window(self):
        game = BreakoutGame()
        start = game.paddle
        game.handle(ord('d'))
        self.assertEqual(game.paddle, start)
        game.update(.15)
        self.assertGreater(game.paddle, start)
        previous = game.paddle
        game.update(.06)
        self.assertGreater(game.paddle, previous)
        game.update(.5)
        previous = game.paddle
        game.update(.2)
        self.assertEqual(game.paddle, previous)
        self.assertEqual(game.balls[0].x, game.paddle)

    def test_launch_aim_changes_direction_and_stays_upward(self):
        game = BreakoutGame()
        for _ in range(30):
            game.handle(ord('j'))
        game.handle(ord(' '))
        self.assertLess(game.balls[0].vx, 0)
        self.assertLess(game.balls[0].vy, -6)
        self.assertAlmostEqual(math.hypot(game.balls[0].vx, game.balls[0].vy), 13)

    def test_direct_large_step_hits_brick_without_tunneling(self):
        game = self.arena()
        game.bricks = [Brick(10, 5), Brick(40, 5)]
        ball = Ball(12, 12, 0, -30)
        game.advance_ball(ball, .4)
        self.assertEqual(len(game.bricks), 1)
        self.assertGreater(ball.vy, 0)
        self.assertGreater(ball.y, 5.85)

    def test_swept_paddle_uses_crossing_position_not_endpoint(self):
        game = self.arena()
        ball = Ball(game.paddle, 18, 20, 20)
        game.advance_ball(ball, .4)
        self.assertLess(ball.vy, 0)
        self.assertLess(ball.y, 19.5)

    def test_wall_reflection_keeps_fast_ball_inside(self):
        game = self.arena()
        ball = Ball(58, 12, 100, 0)
        game.advance_ball(ball, 1)
        self.assertGreaterEqual(ball.x, 0)
        self.assertLessEqual(ball.x, 59)

    def test_reinforced_brick_requires_two_separate_contacts(self):
        game = self.arena()
        brick = Brick(10, 5)
        brick.hp = 2
        game.bricks = [brick, Brick(40, 5)]
        game.advance_ball(Ball(12, 6, 0, -12), .05)
        self.assertIn(brick, game.bricks)
        self.assertEqual(brick.hp, 1)
        game.advance_ball(Ball(12, 6, 0, -12), .05)
        self.assertNotIn(brick, game.bricks)

    def test_explosion_damages_neighbors_and_chains_without_double_scoring(self):
        game = self.arena()
        explosive = Brick(10, 5)
        explosive.kind = 'explosive'
        neighbor = Brick(16, 5)
        neighbor.kind = 'explosive'
        game.bricks = [explosive, neighbor, Brick(22, 5), Brick(46, 5)]
        game.advance_ball(Ball(12, 6, 0, -12), .05)
        self.assertEqual(len(game.bricks), 1)
        self.assertEqual(game.score, 60)

    def test_combo_scores_then_resets_on_paddle_contact(self):
        game = self.arena()
        game.bricks = [Brick(10, 5), Brick(20, 5), Brick(40, 5)]
        game.advance_ball(Ball(12, 6, 0, -12), .05)
        game.advance_ball(Ball(22, 6, 0, -12), .05)
        self.assertEqual(game.score, 30)
        game.advance_ball(Ball(game.paddle, 19, 0, 12), .1)
        self.assertEqual(game.combo, 0)

    def test_stage_clear_waits_then_serves_next_layout_preserving_lives(self):
        game = self.arena()
        game.bricks = [Brick(10, 5)]
        game.balls = [Ball(12, 6, 0, -12)]
        game.lives = 2
        game.update(.05)
        self.assertFalse(game.over)
        self.assertFalse(game.launched)
        self.assertEqual(game.stage, 1)
        game.handle(ord(' '))
        self.assertFalse(game.launched)
        game.update(.5)
        self.assertEqual(game.stage, 1)
        game.update(.8)
        self.assertEqual(game.stage, 2)
        self.assertTrue(game.bricks)
        self.assertEqual(game.lives, 2)
        self.assertFalse(game.launched)
        self.assertEqual(len(game.balls), 1)

    def test_three_layouts_are_distinct_and_final_stage_wins(self):
        game = self.arena()
        self.assertTrue(hasattr(game, 'build_stage'))
        layouts = []
        for stage in range(1, 4):
            game.stage = stage
            game.build_stage()
            layouts.append(tuple((b.x, b.y, b.hp, b.kind) for b in game.bricks))
        self.assertEqual(len(set(layouts)), 3)
        self.assertTrue(any(b.hp > 1 for b in game.bricks))
        self.assertTrue(any(b.kind == 'explosive' for b in game.bricks))
        game.bricks = [Brick(10, 5)]
        game.balls = [Ball(12, 6, 0, -12)]
        game.update(.05)
        self.assertTrue(game.over)
        self.assertIn('CLEAR', game.result)

    def test_wide_expiry_and_motion_keep_paddle_and_serve_inside_field(self):
        game = BreakoutGame()
        game.apply_item('wide')
        game.handle(ord('a'))
        game.update(.5)
        game.wide_timer = .01
        game.update(.02)
        self.assertGreaterEqual(game.paddle - game.paddle_width // 2, 0)
        self.assertLessEqual(game.paddle + game.paddle_width // 2, 59)
        self.assertEqual(game.balls[0].x, game.paddle)

    def test_ball_trails_and_contact_particles_expire(self):
        game = self.arena()
        self.assertTrue(hasattr(game, 'particles'))
        game.balls = [Ball(30, 12, 6, -10)]
        game.update(.1)
        self.assertTrue(game.balls[0].trail)
        game.bricks = [Brick(10, 5), Brick(40, 5)]
        game.advance_ball(Ball(12, 6, 0, -12), .05)
        self.assertTrue(game.particles)
        game.launched = False
        game.update(1)
        self.assertFalse(game.particles)
