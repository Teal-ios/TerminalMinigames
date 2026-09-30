"""Regression checks for terminal input, fair AI and volleyball contact timing."""
import unittest

from games.volley.game import VolleyGame


class VolleyQualityTests(unittest.TestCase):
    def test_movement_is_integrated_and_duplicate_input_does_not_teleport(self):
        one, burst = VolleyGame(), VolleyGame()
        one.handle(ord('d'))
        for _ in range(12):
            burst.handle(ord('d'))
        self.assertEqual(one.players[0][0], 14)
        one.update(.1)
        burst.update(.1)
        self.assertGreater(one.players[0][0], 14)
        self.assertAlmostEqual(one.players[0][0], burst.players[0][0])

    def test_movement_expires_and_slide_clears_old_direction(self):
        game = VolleyGame()
        game.handle(ord('d'))
        game.update(.1)
        game.handle(ord(' '))
        game.update(.65)
        x = game.players[0][0]
        game.update(.2)
        self.assertEqual(game.players[0][0], x)

    def test_movement_without_key_repeats_brakes_to_a_stop(self):
        game = VolleyGame()
        game.handle(ord('d'))
        game.update(.5)
        x = game.players[0][0]
        self.assertGreater(x, 14)
        self.assertLess(x, 18)
        game.update(.2)
        self.assertEqual(game.players[0][0], x)

    def test_jump_pressed_just_before_landing_is_buffered(self):
        game = VolleyGame()
        game.players[0][1:] = [.15, -5]
        game.handle(ord('w'))
        game.update(.08)
        self.assertGreater(game.players[0][1], 0)
        self.assertGreater(game.players[0][2], 0)

    def test_spike_repeat_does_not_extend_active_window(self):
        game = VolleyGame()
        game.jump(0)
        game.handle(ord(' '))
        game.update(.1)
        remaining = game.smash
        game.handle(ord(' '))
        self.assertEqual(game.smash, remaining)

    def spike_contact(self, direction=None):
        game = VolleyGame()
        game.serving = 0
        game.players[0] = [24, 5, 0]
        game.ball = [24, 9, 0, -5]
        if direction:
            game.handle(ord(direction))
        game.handle(ord(' '))
        game.update(.01)
        return game

    def test_airborne_vertical_input_aims_spike(self):
        up, down = self.spike_contact('w'), self.spike_contact('s')
        self.assertGreater(up.ball[3], 0)
        self.assertLess(down.ball[3], -4)
        self.assertGreater(up.ball[2], 0)
        self.assertGreater(down.ball[2], 0)

    def test_airborne_horizontal_input_controls_spike_depth(self):
        short, deep = self.spike_contact('a'), self.spike_contact('d')
        self.assertLess(short.ball[2], deep.ball[2] - 3)

    def test_horizontal_repeats_do_not_keep_old_vertical_aim_alive(self):
        game = VolleyGame()
        game.players[0] = [20, 5, 0]
        game.handle(ord('w'))
        for _ in range(5):
            game.handle(ord('d'))
            game.update(.05)
        game.serving = 0
        x, y, _ = game.players[0]
        game.ball = [x, y + 4, 0, -12]
        game.handle(ord(' '))
        game.update(.01)
        self.assertLess(game.ball[3], 0)

    def test_contact_consumes_spike_and_counts_one_touch(self):
        game = self.spike_contact()
        self.assertEqual(game.smash, 0)
        self.assertEqual(getattr(game, 'rally', None), 1)
        self.assertIn('PERFECT', getattr(game, 'feedback', ''))
        game.update(.03)
        self.assertEqual(game.rally, 1)

    def test_fast_descending_ball_cannot_tunnel_through_player(self):
        game = VolleyGame()
        game.serving = 0
        game.ball = [14, 7, 0, -80]
        game.update(.05)
        self.assertGreater(game.ball[3], 0)
        self.assertEqual(game.scores, [0, 0])

    def test_net_top_bounces_up_instead_of_sideways(self):
        game = VolleyGame()
        game.serving = 0
        game.ball = [30, 8, 0, -10]
        game.update(.06)
        self.assertGreater(game.ball[3], 0)
        self.assertGreater(game.ball[1], 7.5)

    def test_cpu_waits_for_reaction_and_moves_with_speed_limit(self):
        game = VolleyGame()
        game.serving = 0
        game.ball = [56, 14, 0, -2]
        game.update(.02)
        self.assertEqual(game.players[1][0], 46)
        game.update(.24)
        self.assertGreater(game.players[1][0], 46)
        self.assertLessEqual(game.players[1][0], 46 + 11 * .26)

    def test_cpu_predicts_incoming_landing_before_ball_crosses_net(self):
        game = VolleyGame()
        game.serving = 0
        game.ball = [25, 15, 10, 1]
        game.update(.2)
        self.assertLess(getattr(game, 'cpu_target', 60), 44)
        self.assertGreater(game.cpu_target, 30)

    def test_point_keeps_rally_summary_then_resets_for_winners_serve(self):
        game = VolleyGame()
        game.rally = 7
        game.point(0)
        self.assertEqual(getattr(game, 'last_rally', None), 7)
        self.assertEqual(game.rally, 0)
        self.assertEqual(game.server, 0)
        self.assertGreater(game.serving, 0)
        self.assertIn('POINT', getattr(game, 'feedback', ''))

    def test_render_contains_ball_shadow_and_live_rally(self):
        class Canvas:
            def __init__(self):
                self.calls = []

            def text(self, y, x, value, color=0):
                self.calls.append((y, x, str(value)))

            def centered(self, y, value, color=0):
                self.text(y, 0, value, color)

            def border(self, y, height):
                pass

        game = VolleyGame()
        game.ball[0] = 22
        canvas = Canvas()
        game.draw(canvas)
        self.assertTrue(any(y == 25 and x == 24 and value == '_'
                            for y, x, value in canvas.calls))
        self.assertTrue(any('RALLY' in value for _, _, value in canvas.calls))


if __name__ == '__main__':
    unittest.main()
