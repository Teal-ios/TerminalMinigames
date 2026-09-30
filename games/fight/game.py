"""ASCII stick-fighter presentation and keyboard bindings."""
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import curses
import math

from arcade_screen import run
from games.fight.combat import FightGame
from games.fight.moves import ROSTER


class TerminalFight(FightGame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.help_open = False

    def handle(self, key):
        if key in (ord('t'), ord('T')):
            self.help_open = not self.help_open
            return
        if self.help_open:
            return
        mapping = {curses.KEY_LEFT: 'a', curses.KEY_RIGHT: 'd',
                   curses.KEY_UP: 'w', curses.KEY_DOWN: 's', ord(' '): 'guard'}
        action = mapping.get(key)
        if action is None and 0 <= key < 128:
            action = chr(key).lower()
        if action is not None:
            self.press(0, action)

    def update(self, dt):
        if not self.help_open:
            super().update(dt)

    def skill_rows(self, screen, first_row):
        for row, (key, move) in enumerate(ROSTER[self.selected].skills.items(), first_row):
            tags = []
            if move.projectile:
                tags.append('LOW WAVE' if move.height == 'low' else 'WAVE')
            elif move.height == 'grab':
                tags.append('GRAB')
            elif move.height == 'low':
                tags.append('LOW')
            if move.launch:
                tags.append('LAUNCH')
            if move.hits > 1:
                tags.append(f'{move.hits} HITS')
            if move.armor:
                tags.append('ARMOR')
            if move.breaker:
                tags.append('GUARD BREAK')
            screen.text(row, 3, f'{key.upper()}  {move.name:<15} {move.cost:3} MP  ' + '/'.join(tags), 2)

    def draw(self, screen):
        screen.centered(0, 'S T I C K   C L A S H', 1)
        if self.phase == 'select':
            self.draw_select(screen)
            return
        if self.help_open:
            self.draw_help(screen)
            return
        screen.centered(2, f'ROUND {self.round}    YOU {self.wins[0]} : {self.wins[1]} CPU    TIME {math.ceil(self.remaining):02}', 2)
        for side, fighter in enumerate(self.fighters):
            col = 1 if side == 0 else 34
            screen.text(3, col, ('YOU ' if side == 0 else 'CPU ') + fighter.profile.name, 1 if side == 0 else 3)
            filled = math.ceil(18 * fighter.hp / fighter.profile.hp)
            screen.text(4, col, f'HP [{"#" * filled}{"." * (18 - filled)}] {fighter.hp:3}', 4 if fighter.hp > 25 else 3)
            meter = int(fighter.meter // 10)
            screen.text(5, col, f'MP [{"=" * meter}{"." * (10 - meter)}] {int(fighter.meter):3}', 2)
        active_combo = next((fighter for fighter in self.fighters if fighter.combo_timer > 0 and fighter.combo_hits >= 2), None)
        if active_combo:
            screen.centered(6, f'{active_combo.profile.name}: {active_combo.combo_hits} HIT COMBO / {active_combo.combo_damage} DAMAGE', 2)
        if self.throw:
            screen.centered(7, 'GRABBED! PRESS G NOW!' if self.throw.owner == 1 else 'THROW ATTEMPT!', 3)
        elif self.phase == 'between' or self.message_timer > 0:
            screen.centered(7, self.message, 2)
        screen.border(8, 18)
        screen.text(24, 1, '_' * 62, 1)
        # City silhouettes keep the arena readable behind the moving fighters.
        screen.text(10, 4, ' _[]_       ___           _[]_        ___      _[]_', 0)
        screen.text(11, 4, '|    |     |   |         |    |      |   |    |   |', 0)
        for side, fighter in enumerate(self.fighters):
            self.draw_fighter(screen, fighter, side)
        for shot in self.projectiles:
            y = max(9, min(24, 24 - int(shot.y)))
            for offset, char in enumerate('=O>' if shot.vx > 0 else '<O='):
                x = 1 + int(shot.x) + offset
                if 1 <= x <= 62:
                    screen.text(y, x, char, 2 if shot.owner == 0 else 3)
        screen.text(27, 1, 'A/D Move  W Jump  S Duck  E Dash  SPACE Guard')
        screen.text(28, 1, 'J Jab  K Heavy  L Kick  U Launch  O Grab  G Break')
        screen.text(29, 1, 'I/Z/X/C Skills  H Super  T Help  P Pause  R Restart')
        screen.text(31, 1, 'Chains: J>J>K  J>L>K  L>L>K     Q/ESC: Quit', 1)

    def draw_select(self, screen):
        screen.centered(2, '1 vs CPU / FIRST TO 2 ROUNDS / 60 SECONDS', 2)
        screen.text(4, 3, 'YOUR FIGHTER: ' + ROSTER[self.selected].name, 1)
        screen.text(5, 3, ROSTER[self.selected].description)
        for index, profile in enumerate(ROSTER):
            marker = '>' if index == self.selected else ' '
            screen.text(8 + index, 3, f'{marker} {index + 1}  {profile.name:<8} HP {profile.hp:3}', 2 if index == self.selected else 0)
        cpu_name = 'RANDOM' if self.cpu_selected is None else ROSTER[self.cpu_selected].name
        screen.text(12, 3, 'CPU FIGHTER: ' + cpu_name, 3)
        screen.text(13, 3, '4 STRIKER   5 RUSH   6 IRON   0 RANDOM')
        screen.text(17, 3, 'YOUR SPECIAL MOVES / METER COST', 1)
        self.skill_rows(screen, 19)
        screen.text(26, 3, 'J/K/L attacks + U launcher + O grab + G throw break')
        screen.text(28, 3, 'Each fighter: 4 unique skills + 1 super + common moves')
        screen.text(30, 3, 'Choose, then ENTER to fight. In match: T for move list.')

    def draw_help(self, screen):
        screen.centered(2, 'MOVE LIST - GAME PAUSED - T TO RETURN', 2)
        screen.text(4, 2, 'J Jab (high)   K Heavy (mid)   L Side kick (mid)')
        screen.text(5, 2, 'S then L: low sweep   W then L: flying kick')
        screen.text(6, 2, 'U: launcher -> J/L follow-up for an air combo')
        screen.text(7, 2, 'O: close-range grab, ignores guard   G: throw break')
        screen.text(9, 2, 'SPACE: standing guard   S then SPACE: low guard')
        screen.text(10, 2, 'Low attacks beat standing guard. Mid beats low guard.')
        screen.text(11, 2, 'Duck avoids high jabs/grabs. Jump avoids low attacks.')
        screen.text(13, 2, 'J>J>K Rush Finish   J>L>K Spin Launch   L>L>K Axe Finish')
        screen.text(14, 2, 'Queue up to 3 inputs. Follow-ups cancel on a hit.')
        screen.text(15, 2, 'Combos scale damage; 6 hits force a knockdown.')
        screen.text(17, 2, ROSTER[self.selected].name + ' SPECIAL MOVES', 1)
        self.skill_rows(screen, 19)
        screen.text(25, 2, 'Land hits/build meter, then spend it on special moves.')
        screen.text(27, 2, 'R: rematch with same choices (random CPU rerolls).')
        screen.text(29, 2, 'Q: quit. Run arcade fight again to change characters.')

    def draw_fighter(self, screen, fighter, side):
        pose = ['   O     ', '  /|\\    ', '   |     ', '  / \\    ', ' /   \\   ']
        if fighter.down > 0:
            pose = [' __o____ ']
        elif self.throw is not None:
            pose = ['   O     ', '  /|==>  ', '   |     ', '  / \\    ', ' /   \\   ']
        elif fighter.stun > 0:
            pose = ['  *O*    ', '  \\|/    ', '   |     ', '  / \\    ', ' /   \\   ']
        elif fighter.attack:
            move = fighter.attack.move
            if 'KICK' in move.name or 'SWEEP' in move.name or 'AXE' in move.name:
                pose = ['   O     ', '  /|\\    ', '   |___> ', '  /      ', ' /       ']
            elif move.height == 'grab':
                pose = ['   O     ', '  /|--{  ', '   |     ', '  / \\    ', ' /   \\   ']
            elif move.launch:
                pose = ['   O  /  ', '  /| /   ', '   |     ', '  / \\    ', ' /   \\   ']
            else:
                pose = ['   O     ', '  /|===> ', '   |     ', '  / \\    ', ' /   \\   ']
        elif fighter.guard > 0:
            pose = ['   O |   ', '  /|]|   ', '   |     ', '  / \\    ', ' /   \\   ']
        elif fighter.crouch > 0:
            pose = ['   o     ', '  /|>    ', ' _/ \\_   ']
        elif fighter.y > 0:
            pose = ['   O     ', '  /|\\    ', '   |     ', ' _/ \\_   ']
        elif fighter.dash > 0:
            pose = ['    O    ', ' --/|>   ', '   /     ', ' _/ \\    ']
        color = 1 if side == 0 else 3
        bottom = 24 - int(fighter.y)
        for index, line in enumerate(pose):
            if fighter.facing < 0:
                line = line[::-1].translate(str.maketrans('/\\<>{}', '\\/><}{'))
            y = bottom - len(pose) + 1 + index
            for offset, char in enumerate(line):
                x = 2 + int(fighter.x) - 4 + offset
                if char != ' ' and 1 <= x <= 62 and 9 <= y <= 24:
                    screen.text(y, x, char, color)


def main():
    return run(TerminalFight)


if __name__ == '__main__':
    raise SystemExit(main())
