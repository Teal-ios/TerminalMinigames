import math
import unittest

from games.fight.combat import Attack, Fighter
from games.fight.moves import BASIC, ROSTER
from games.fight.render import limb_pose


class AnimationContinuityTests(unittest.TestCase):
    def test_quake_fist_strikes_low_with_hand_and_cyclone_kick_uses_foot(self):
        fighter = Fighter(ROSTER[2], 20)
        move = ROSTER[2].skills['z']
        fighter.attack = Attack(move, elapsed=move.startup)
        self.assertLess(limb_pose(fighter, 1)['hand'][1], 5)
        fighter = Fighter(ROSTER[1], 20)
        move = ROSTER[1].skills['z']
        fighter.attack = Attack(move, elapsed=move.startup)
        self.assertGreater(limb_pose(fighter, 1)['foot'][1], 20)

    def test_attack_pose_does_not_snap_when_strike_becomes_active(self):
        for profile in ROSTER:
            for move in list(BASIC.values()) + list(profile.skills.values()):
                with self.subTest(character=profile.name, move=move.name):
                    fighter = Fighter(profile, 20)
                    fighter.attack = Attack(move, elapsed=move.startup - .001)
                    before = limb_pose(fighter, 1)
                    fighter.attack.elapsed = move.startup + .001
                    after = limb_pose(fighter, 1)
                    self.assertLess(max(math.dist(before[key], after[key]) for key in before), 2)

    def test_pose_returns_to_idle_at_end_of_recovery(self):
        for move in BASIC.values():
            with self.subTest(move=move.name):
                fighter = Fighter(ROSTER[0], 20)
                fighter.attack = Attack(move, elapsed=move.duration - .001)
                before = limb_pose(fighter, 1)
                fighter.attack = None
                after = limb_pose(fighter, 1)
                self.assertLess(max(math.dist(before[key], after[key]) for key in before), 1)
