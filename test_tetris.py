import random
import unittest

from games.tetris.game import TetrisGame, Piece


class TetrisTests(unittest.TestCase):
    def game(self):
        return TetrisGame(rng=random.Random(7))

    def test_each_bag_contains_all_seven_pieces(self):
        game = self.game()
        sequence = []
        for _ in range(14):
            sequence.append(game.active.kind)
            game.spawn()
        self.assertEqual(set(sequence[:7]), set('IOTSZJL'))
        self.assertEqual(set(sequence[7:]), set('IOTSZJL'))

    def test_movement_stays_inside_walls(self):
        game = self.game()
        for _ in range(20): game.handle(ord('a'))
        self.assertGreaterEqual(min(x for x, y in game.cells()), 0)
        for _ in range(20): game.handle(ord('d'))
        self.assertLess(max(x for x, y in game.cells()), 10)

    def test_four_rotations_return_to_same_shape(self):
        game = self.game()
        game.active = Piece('T', 3, 4)
        before = set(game.cells())
        for _ in range(4): game.handle(ord('w'))
        self.assertEqual(set(game.cells()), before)

    def test_rotation_near_wall_kicks_into_valid_position(self):
        game = self.game()
        game.active = Piece('I', -2, 4, 1)
        self.assertTrue(game.valid(game.active))
        game.handle(ord('w'))
        self.assertEqual(game.active.rotation, 2)
        self.assertTrue(game.valid(game.active))

    def test_hard_drop_lands_at_ghost_and_locks(self):
        game = self.game()
        landing = set(game.cells(y=game.ghost_y()))
        game.handle(ord(' '))
        self.assertTrue(all(game.board[y][x] for x,y in landing))
        self.assertGreater(game.score, 0)

    def test_soft_drop_moves_one_row_and_scores(self):
        game = self.game()
        y = game.active.y
        game.handle(ord('s'))
        self.assertEqual(game.active.y, y + 1)
        self.assertEqual(game.score, 1)

    def test_hold_only_once_until_piece_locks(self):
        game = self.game()
        first = game.active.kind
        game.handle(ord('c'))
        second = game.active.kind
        self.assertEqual(game.held, first)
        game.handle(ord('c'))
        self.assertEqual(game.active.kind, second)
        game.handle(ord(' '))
        game.handle(ord('c'))
        self.assertEqual(game.active.kind, first)

    def clear_four(self):
        game = self.game()
        game.board[16:] = [['J'] * 4 + [None] + ['J'] * 5 for _ in range(4)]
        game.active = Piece('I', 2, 16, 1)
        game.lock()
        return game

    def test_clear_animation_preserves_board_and_blocks_input_until_finished(self):
        game = self.clear_four()
        self.assertEqual(game.clear_rows, [16,17,18,19])
        board = [row[:] for row in game.board]
        for key in 'acw ': game.handle(ord(key))
        game.update(.2)
        self.assertEqual(game.board, board)
        self.assertIsNone(game.active)
        game.update(.4)
        self.assertEqual(game.lines, 4)
        self.assertEqual(game.score, 800)
        self.assertFalse(any(any(row) for row in game.board))
        self.assertIsNotNone(game.active)

    def test_clear_collapses_survivors_without_aliasing_rows(self):
        game = self.clear_four()
        game.board[15][0] = 'Z'
        game.update(.6)
        self.assertEqual(game.board[19][0], 'Z')
        game.board[0][0] = 'T'
        self.assertIsNone(game.board[1][0])

    def test_grounded_piece_has_lock_delay(self):
        game = self.game()
        game.active = Piece('O', 4, 18)
        game.update(.2)
        self.assertFalse(any(any(row) for row in game.board))
        game.update(.25)
        self.assertTrue(any(any(row) for row in game.board))

    def test_leaving_ledge_cannot_refresh_exhausted_lock_budget(self):
        game = self.game()
        game.board[19][4] = 'J'
        game.active = Piece('O', 4, 17)
        game.lock_resets, game.lock_clock = 12, .35
        for _ in range(6):
            game.handle(ord('d'))
            game.update(.01)
            game.handle(ord('a'))
            game.update(.01)
        self.assertEqual(game.board[17][4], 'O')
        self.assertEqual(game.board[18][5], 'O')

    def test_blocked_spawn_ends_game(self):
        game = self.game()
        game.board[0] = ['Z'] * 10
        game.spawn('O')
        self.assertTrue(game.over)

    def test_hidden_locked_cells_top_out_without_negative_index_writes(self):
        game = self.game()
        game.active = Piece('O', 4, -1)
        game.lock()
        self.assertTrue(game.over)
        self.assertFalse(any(game.board[-1]))

    def test_level_speeds_up_and_restart_preserves_best_only(self):
        game = self.game()
        interval = game.gravity_interval
        game.lines, game.score = 10, 500
        self.assertEqual(game.level, 2)
        self.assertLess(game.gravity_interval, interval)
        restarted = game.restart()
        self.assertEqual(restarted.best, 500)
        self.assertEqual(restarted.lines, 0)
        self.assertEqual(restarted.score, 0)
