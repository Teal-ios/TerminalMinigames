"""A small Pikachu-inspired terminal volleyball match against the CPU."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import curses

from arcade_screen import run

W, H, NET = 60, 22, 30


class VolleyGame:
    def __init__(self):
        # Player coordinates use height above the ground, unlike screen rows.
        self.players = [[14.0, 0.0, 0.0], [46.0, 0.0, 0.0]]
        self.scores = [0, 0]
        self.over = False
        self.result = ''
        self.smash = 0.0
        self.bounce_cooldown = [0.0, 0.0]
        self.serve(0)

    def serve(self, side):
        self.serving = 1.2
        self.server = side
        self.ball = [14.0 if side == 0 else 46.0, 12.0,
                     8.0 if side == 0 else -8.0, 4.0]
        self.players = [[14.0, 0.0, 0.0], [46.0, 0.0, 0.0]]
        self.bounce_cooldown = [0.0, 0.0]
        self.smash = 0.0
        self.slide_timer = [0.0, 0.0]
        self.recovery = [0.0, 0.0]
        self.facing = [1, -1]

    def lying_down(self, side):
        return self.slide_timer[side] > 0 or self.recovery[side] > 0

    def slide(self, side, direction):
        if not self.lying_down(side) and self.players[side][1] == 0 and self.players[side][2] == 0:
            self.slide_timer[side] = 0.34
            self.facing[side] = direction

    def jump(self, side):
        player = self.players[side]
        if player[1] == 0 and not self.lying_down(side):
            player[2] = 16.0

    def handle(self, key):
        if self.lying_down(0):
            return
        if key in (curses.KEY_LEFT, ord('a'), ord('A')):
            self.facing[0] = -1
            self.players[0][0] = max(4, self.players[0][0] - 1.5)
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
            self.facing[0] = 1
            self.players[0][0] = min(NET - 4, self.players[0][0] + 1.5)
        elif key in (curses.KEY_UP, ord('w'), ord('W')):
            self.jump(0)
        elif key == ord(' '):
            if self.players[0][1] > 0 or self.players[0][2] > 0:
                self.smash = 0.4
            else:
                self.slide(0, self.facing[0])

    def point(self, side):
        self.scores[side] += 1
        if self.scores[side] >= 5:
            self.over = True
            self.result = 'YOU WIN!' if side == 0 else 'CPU WINS - TRY AGAIN!'
        else:
            self.serve(side)

    def update(self, dt):
        if self.over:
            return
        self.smash = max(0, self.smash - dt)
        self.bounce_cooldown = [max(0, value - dt) for value in self.bounce_cooldown]
        for side in (0, 1):
            if self.slide_timer[side] > 0:
                duration = min(dt, self.slide_timer[side])
                self.players[side][0] += self.facing[side] * 27 * duration
                low, high = (4, NET - 4) if side == 0 else (NET + 4, W - 4)
                self.players[side][0] = max(low, min(high, self.players[side][0]))
                self.slide_timer[side] = max(0, self.slide_timer[side] - dt)
                if self.slide_timer[side] == 0:
                    self.recovery[side] = max(0, 0.18 - (dt - duration))
            else:
                self.recovery[side] = max(0, self.recovery[side] - dt)
        cpu = self.players[1]
        bx, by, vx, vy = self.ball
        target = max(NET + 4, min(W - 4, bx + vx * 0.18)) if bx > NET else 44
        if not self.lying_down(1):
            cpu[0] += max(-10 * dt, min(10 * dt, target - cpu[0]))
            if not self.serving and bx > NET and vy < 0:
                if by < 4 and 3.8 < abs(bx - cpu[0]) < 10:
                    self.slide(1, 1 if bx > cpu[0] else -1)
                elif abs(bx - cpu[0]) < 3 and 4 < by < 10:
                    self.jump(1)
        for player in self.players:
            if player[1] > 0 or player[2] > 0:
                player[2] -= 28 * dt
                player[1] += player[2] * dt
                if player[1] <= 0:
                    player[1] = player[2] = 0.0
        if self.serving > 0:
            self.serving = max(0, self.serving - dt)
            return

        old_x, old_y = bx, by
        vy -= 14 * dt
        bx += vx * dt
        by += vy * dt
        if bx < 1:
            bx, vx = 1, abs(vx)
        elif bx > W - 1:
            bx, vx = W - 1, -abs(vx)
        if by > H - 1:
            by, vy = H - 1, -abs(vy)

        # A swept test catches the ball crossing either face of the net.
        if by <= 7.5:
            if old_x < NET and bx >= NET - 0.6:
                bx, vx = NET - 0.7, -abs(vx)
            elif old_x > NET and bx <= NET + 0.6:
                bx, vx = NET + 0.7, abs(vx)
        if abs(bx - NET) <= 0.7 and old_y > 7.5 >= by:
            by, vy = 7.6, abs(vy) * 0.85

        for side, (px, py, player_vy) in enumerate(self.players):
            if self.bounce_cooldown[side] > 0:
                continue
            if (side == 0 and bx >= NET) or (side == 1 and bx <= NET):
                continue
            # The face/body receive the ball; the tall ear tips are decorative.
            low_pose = self.lying_down(side)
            head = 1.3 if low_pose else py + 4
            reach = 5.2 if low_pose else 3.8
            if abs(bx - px) <= reach and head - 1 <= by <= head + 1.3 and vy < player_vy:
                direction = 1 if side == 0 else -1
                by = head + 1.4
                vx, vy = direction * 10 + (bx - px) * 1.4, 15.0
                if side == 0 and self.smash > 0 and py > 0:
                    vx = 22.0
                    vy = -3.0 if by > 8.5 else 15.0
                elif side == 1 and py > 1 and by > 9:
                    vx, vy = -16.0, 1.0
                self.bounce_cooldown[side] = 0.25
        self.ball = [bx, by, vx, vy]
        if by <= 0.6:
            self.point(1 if bx < NET else 0)

    def draw(self, screen):
        screen.centered(0, 'P I K A   V O L L E Y', 2)
        screen.centered(2, f'YOU  {self.scores[0]}   :   {self.scores[1]}  CPU     FIRST TO 5', 1)
        screen.border(3, H + 2)

        def court(x, y, text, color=0):
            screen.text(4 + H - 1 - int(y), 2 + int(x), text, color)

        for y in range(7):
            court(NET, y, '|', 1)
        court(NET, 7, '+', 1)
        for side, (x, y, _) in enumerate(self.players):
            self.draw_pikachu(court, side, x, y)
        court(self.ball[0], self.ball[1], 'O', 3)
        if self.serving > 0 and not self.over:
            screen.centered(6, 'YOUR SERVE' if self.server == 0 else 'CPU SERVE', 2)
        screen.text(28, 1, 'LEFT/RIGHT or A/D: Move  UP/W: Jump  SPACE: Slide/Spike')
        screen.text(29, 1, 'P: Pause  R: Restart  Q: Quit')
        status = 'SLIDING!' if self.slide_timer[0] > 0 else 'GETTING UP...' if self.recovery[0] > 0 else ''
        screen.text(31, 1, status or 'SPACE on ground: slide. SPACE in air: spike.', 2)

    def draw_pikachu(self, court, side, x, y):
        """Layer an ASCII sprite; clip its tail against court boundaries."""
        left, right = (0, NET - 1) if side == 0 else (NET + 1, W - 1)

        def paint(dx, dy, text, color=2):
            for index, char in enumerate(text):
                col, row = int(x) + dx + index, int(y) + dy
                if char != ' ' and left <= col <= right and 0 <= row < H:
                    court(col, row, char, color)

        if self.lying_down(side):
            rows = ['    /\\_/\\   ', ' __/ o.o \\__ ', '(_(o_w_o)_)=>']
            mirrored = self.facing[side] < 0
            for index, row in enumerate(rows):
                if mirrored:
                    row = row[::-1].translate(str.maketrans('/\\()<>', '\\/)(><'))
                paint(-6, 2 - index, row)
            paint(-3 if not mirrored else 0, 0, 'o', 3)
            paint(1 if not mirrored else 4, 0, 'o', 3)
            if self.slide_timer[side] > 0:
                paint(-9 if not mirrored else 7, 0, '--', 0)
            if side == 1:
                paint(-1, 1, '===', 1)
            return

        # A zigzag tail points away from the net, behind the body.
        tail = [(-8, 4, ' __'), (-8, 3, '/_/'), (-7, 2, '\\_\\'), (-6, 1, '/_/')]
        for dx, dy, text in tail:
            if side == 1:
                dx = -dx - len(text) + 1
                text = text[::-1].translate(str.maketrans('/\\', '\\/'))
            paint(dx, dy, text)

        attacking = side == 0 and self.smash > 0
        rows = [
            ' /\\   /\\ ',
            ' |/\\ /\\| ',
            ' /     \\ ',
            '( o . o )',
            '(o  w  o)',
            ' /|   |\\ ',
            '(_/___\\_)',
        ]
        if y > 0:
            rows[5], rows[6] = '\\ |   | /', ' (_/ \\_) '
        if attacking:
            rows[3], rows[5] = '( > . < )', '\\ |   | /'
        for index, row in enumerate(rows):
            paint(-4, 6 - index, row)
        paint(-3, 6, '/\\', 5)
        paint(2, 6, '/\\', 5)
        paint(-2, 3, '>' if attacking else 'o', 0)
        paint(2, 3, '<' if attacking else 'o', 0)
        paint(0, 3, '.', 0)
        paint(0, 2, 'w', 0)
        paint(-3, 2, 'o', 3)
        paint(3, 2, 'o', 3)
        if side == 1:
            paint(-1, 4, '===', 1)  # CPU's blue headband.
        if attacking:
            paint(5, 5, '*', 3)


def main():
    return run(VolleyGame)


if __name__ == '__main__':
    raise SystemExit(main())
