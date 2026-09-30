"""Animated terminal stick-fighter presentation and keyboard bindings."""
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import curses
import math

from arcade_screen import run
from games.fight.combat import FightGame, Fighter
from games.fight.moves import ROSTER
from games.fight.render import Surface, draw_arena, figure


class TerminalFight(FightGame):
    start_prompt_row = 31

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.help_open = False
        self.range_guide = False

    def handle(self, key):
        if key in (ord('b'), ord('B')):
            self.range_guide = not self.range_guide
            return
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
        screen.centered(0, 'S T I C K   C L A S H  /  OVERDRIVE', 1)
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
            trail = max(filled, math.ceil(18 * self.health_trail[side] / fighter.profile.hp))
            screen.text(4, col, f'HP [{"." * 18}] {fighter.hp:3}', 7)
            screen.text(4, col + 4, '=' * trail, 3)
            screen.text(4, col + 4, '#' * filled, 4 if fighter.hp > fighter.profile.hp / 4 else 3)
            meter = int(fighter.meter // 10)
            screen.text(5, col, f'MP [{"=" * meter}{"." * (10 - meter)}] {int(fighter.meter):3}', 2)
        active_combo = next((fighter for fighter in self.fighters if fighter.combo_timer > 0 and fighter.combo_hits >= 2), None)
        if active_combo:
            screen.centered(6, f'<< {active_combo.combo_hits:02} HITS >>  {active_combo.combo_damage} DAMAGE  /  {active_combo.profile.name}', 2)
        if self.throw:
            screen.centered(7, 'GRABBED! PRESS G NOW!' if self.throw.owner == 1 else 'THROW ATTEMPT!', 3)
        elif self.phase == 'between' or self.message_timer > 0:
            screen.centered(7, self.message, 2)
        screen.border(8, 18)
        draw_arena(screen, self, self.range_guide)
        player = self.fighters[0]
        distance = abs(player.x - self.fighters[1].x)
        link = player.attack and player.attack.confirmed and player.attack.resolved >= player.attack.move.hits
        screen.text(26, 1, 'HIT CONFIRMED - LINK YOUR NEXT ATTACK!' if link
                    else f'GAP {distance:4.1f}   JAB {5.5 * player.profile.reach_scale:.1f}   KICK {7 * player.profile.reach_scale:.1f}   B: Range guide', 2 if link else 7)
        screen.text(27, 1, 'A/D Move  W Jump  S Duck  E Dash  SPACE Guard')
        screen.text(28, 1, 'J Jab  K Heavy  L Kick  U Launch  O Grab  G Break')
        screen.text(29, 1, 'I/Z/X/C Skills  H Super  T Help  P Pause  R Restart')
        inputs = ' > '.join(key.upper() for key, _ in player.history)
        screen.text(30, 1, f'INPUT: {inputs or "-"}   /   {player.last_move or "Keep your distance. Find an opening."}', 7)
        screen.text(31, 1, 'Chains: J>J>K  J>L>K  L>L>K     Q/ESC: Quit', 1)

    def draw_select(self, screen):
        screen.centered(2, 'CHOOSE YOUR STYLE  /  FIRST TO TWO', 2)
        screen.text(4, 3, 'YOU: ' + ROSTER[self.selected].name + '   [1 / 2 / 3]', 1)
        cpu_name = 'RANDOM' if self.cpu_selected is None else ROSTER[self.cpu_selected].name
        screen.text(5, 3, 'CPU FIGHTER: ' + cpu_name, 3)
        screen.text(6, 3, 'CPU: 4 STRIKER / 5 RUSH / 6 IRON / 0 RANDOM')
        portraits = Surface(62, 11)
        for index, profile in enumerate(ROSTER):
            x = 10 + index * 20
            fighter = Fighter(profile, x)
            figure(portraits, fighter, 0.5 + index, floor=39)
            screen.text(8, x - 3, ('>' if index == self.selected else ' ') + profile.name, profile.color)
        portraits.flush(screen, top=9)
        screen.centered(20, ROSTER[self.selected].concept, ROSTER[self.selected].color)
        self.skill_rows(screen, 22)
        screen.text(28, 3, 'J/K/L attacks  U launch  O grab  G break  T move list')
        screen.text(29, 3, 'Keep distance. Confirm a hit. Link into your finisher.')

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
        screen.text(28, 2, 'B: show attack reach. Hit sparks freeze the action briefly.')
        screen.text(29, 2, 'Q: quit. Run arcade fight again to change characters.')


def main():
    return run(TerminalFight)


if __name__ == '__main__':
    raise SystemExit(main())
