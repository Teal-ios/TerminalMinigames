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

    def jump(self, side):
        player = self.players[side]
        if player[1] == 0:
            player[2] = 16.0

    def handle(self, key):
        if key in (curses.KEY_LEFT, ord('a'), ord('A')):
            self.players[0][0] = max(3, self.players[0][0] - 1.5)
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
            self.players[0][0] = min(NET - 3, self.players[0][0] + 1.5)
        elif key in (curses.KEY_UP, ord('w'), ord('W')):
            self.jump(0)
        elif key == ord(' '):
            self.smash = 0.4
            self.jump(0)

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
        cpu = self.players[1]
        bx, by, vx, vy = self.ball
        target = max(NET + 3, min(W - 3, bx + vx * 0.18)) if bx > NET else 44
        cpu[0] += max(-10 * dt, min(10 * dt, target - cpu[0]))
        if not self.serving and bx > NET and abs(bx - cpu[0]) < 3 and 4 < by < 10 and vy < 0:
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
            head = py + 3
            if abs(bx - px) <= 2.4 and head - 1 <= by <= head + 1.3 and vy < player_vy:
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
            color = 2 if side == 0 else 4
            court(x - 1, y + 2, 'V V', color)
            court(x - 1, y + 1, 'o.o', color)
            court(x - 1, y, '/w\\', color)
        court(self.ball[0], self.ball[1], 'O', 3)
        if self.serving > 0 and not self.over:
            screen.centered(6, 'YOUR SERVE' if self.server == 0 else 'CPU SERVE', 2)
        screen.text(28, 1, 'LEFT/RIGHT or A/D: Move  UP/W: Jump  SPACE: Spike')
        screen.text(29, 1, 'P: Pause  R: Restart  Q: Quit')
        screen.text(31, 1, 'Get under the ball to return it. Jump + spike to attack!')


def main():
    return run(VolleyGame)


if __name__ == '__main__':
    raise SystemExit(main())
