import unittest
from games.fight.game import TerminalFight


class TrainingTests(unittest.TestCase):
    def training(self):
        game = TerminalFight(cpu_selected=0)
        game.handle_menu(ord('9'))
        game.start()
        return game

    def test_training_has_full_meter_and_frozen_round_clock(self):
        game = self.training()
        game.update(.5)
        self.assertEqual(game.remaining, 60)
        self.assertEqual(game.fighters[0].meter, 100)
        self.assertIsNone(game.fighters[1].attack)

    def test_dummy_can_guard_for_throw_practice(self):
        game = self.training()
        game.handle(ord('y'))
        game.update(.1)
        self.assertTrue(game.guarding(game.fighters[1]))

    def test_training_ko_resets_without_match_win(self):
        game = self.training()
        game.fighters[1].hp = 0
        game.update(.01)
        self.assertEqual(game.wins, [0, 0])
        self.assertFalse(game.over)
        game.update(2)
        self.assertEqual(game.round, 1)
        self.assertEqual(game.fighters[1].hp, 100)

    def test_restart_preserves_training_mode(self):
        game = self.training().restart()
        game.start()
        game.update(.1)
        self.assertEqual(game.fighters[0].meter, 100)

    def test_menu_can_return_to_normal_match(self):
        game = TerminalFight(cpu_selected=0)
        game.handle_menu(ord('9'))
        game.handle_menu(ord('9'))
        game.start()
        game.update(.1)
        self.assertLess(game.remaining, 60)
        self.assertEqual(game.fighters[0].meter, 0)
