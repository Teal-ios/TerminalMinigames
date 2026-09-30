"""Terminal breakout with falling power-ups and up to eight balls."""
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import curses
from dataclasses import dataclass
import math
import random

from arcade_screen import run

W, H, PADDLE_Y = 60, 22, 20
MAX_BALLS = 8
ITEMS = {
    'double': ('2', 'MULTIBALL x2!', 2),
    'wide': ('W', 'WIDE PADDLE - 12s', 4),
    'slow': ('S', 'SLOW BALLS - 8s', 1),
    'life': ('+', 'EXTRA LIFE!', 3),
}


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float


@dataclass
class Brick:
    x: float
    y: float
    width: int = 5


@dataclass
class Item:
    x: float
    y: float
    kind: str


class BreakoutGame:
    def __init__(self, rng=None):
        self.rng = rng if rng is not None else random.Random()
        self.paddle = W / 2
        self.lives, self.score = 3, 0
        self.bricks = [Brick(6 * col + 1, row + 2)
                       for row in range(5) for col in range(10)]
        self.balls = [Ball(self.paddle, PADDLE_Y - 1, 0, 0)]
        self.items = []
        self.wide_timer = self.slow_timer = self.message_timer = 0.0
        self.message = ''
        self.launched = self.over = False
        self.result = ''

    @property
    def paddle_width(self):
        return 15 if self.wide_timer > 0 else 9

    def clamp_paddle(self):
        half = self.paddle_width // 2
        self.paddle = max(half, min(W - 1 - half, self.paddle))

    def handle(self, key):
        if key in (curses.KEY_LEFT, ord('a'), ord('A')):
            self.paddle -= 2
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
            self.paddle += 2
        elif key in (ord(' '), 10, 13) and not self.launched:
            self.launched = True
            self.balls[0].vx, self.balls[0].vy = 5.0, -12.0
        self.clamp_paddle()
        if not self.launched:
            self.balls[0].x = self.paddle

    def apply_item(self, kind):
        self.message = ITEMS[kind][1]
        self.message_timer = 2.5
        if kind == 'double':
            original = list(self.balls)
            for index, ball in enumerate(original):
                if len(self.balls) >= MAX_BALLS:
                    break
                # Rotate each copy, preserving speed and avoiding flat trajectories.
                angle = math.radians(28 if index % 2 == 0 else -28)
                vx = ball.vx * math.cos(angle) - ball.vy * math.sin(angle)
                vy = ball.vx * math.sin(angle) + ball.vy * math.cos(angle)
                speed = math.hypot(ball.vx, ball.vy)
                if abs(vy) < speed * 0.35:
                    vy = math.copysign(speed * 0.35, ball.vy or -1)
                    vx = math.copysign(math.sqrt(max(0, speed * speed - vy * vy)), vx)
                self.balls.append(Ball(ball.x, ball.y, vx, vy))
        elif kind == 'wide':
            self.wide_timer = 12.0
            self.clamp_paddle()
        elif kind == 'slow':
            self.slow_timer = 8.0
        elif kind == 'life':
            self.lives = min(5, self.lives + 1)

    def advance_ball(self, ball, dt):
        old_x, old_y = ball.x, ball.y
        ball.x += ball.vx * dt
        ball.y += ball.vy * dt
        if ball.x < 0:
            ball.x, ball.vx = -ball.x, abs(ball.vx)
        elif ball.x > W - 1:
            ball.x, ball.vx = 2 * (W - 1) - ball.x, -abs(ball.vx)
        if ball.y < 0:
            ball.y, ball.vy = -ball.y, abs(ball.vy)

        if (ball.vy > 0 and old_y < PADDLE_Y - 0.5 <= ball.y
                and abs(ball.x - self.paddle) <= self.paddle_width / 2):
            offset = max(-1, min(1, (ball.x - self.paddle) / (self.paddle_width / 2)))
            angle = offset * math.radians(62)
            speed = max(13, math.hypot(ball.vx, ball.vy))
            ball.vx = math.sin(angle) * speed
            ball.vy = -math.cos(angle) * speed
            ball.y = PADDLE_Y - 0.51

        for brick in self.bricks:
            if (brick.x - 0.85 <= ball.x <= brick.x + brick.width - 0.15
                    and brick.y - 0.85 <= ball.y <= brick.y + 0.85):
                if old_y < brick.y - 0.85 or old_y > brick.y + 0.85:
                    ball.vy = -ball.vy
                    ball.y = old_y
                else:
                    ball.vx = -ball.vx
                    ball.x = old_x
                self.bricks.remove(brick)
                self.score += 10
                if self.rng.random() < 0.30:
                    kind = self.rng.choice(tuple(ITEMS))
                    self.items.append(Item(brick.x + brick.width // 2, brick.y + 1, kind))
                break

    def update(self, dt):
        if self.over:
            return
        self.message_timer = max(0, self.message_timer - dt)
        self.wide_timer = max(0, self.wide_timer - dt)
        self.slow_timer = max(0, self.slow_timer - dt)
        if not self.launched:
            return
        # No ball travels more than 0.3 cells per step, including during slow frames.
        speed = max((max(abs(b.vx), abs(b.vy)) for b in self.balls), default=13)
        steps = max(1, math.ceil(dt * speed / 0.3))
        for _ in range(steps):
            tick = dt / steps
            for ball in self.balls:
                self.advance_ball(ball, tick * (0.65 if self.slow_timer > 0 else 1))
            self.balls = [ball for ball in self.balls if ball.y < H]
            if not self.bricks:
                self.over = True
                self.result = f'ALL CLEAR! SCORE {self.score}'
                return
            if not self.balls:
                self.lives -= 1
                self.items.clear()
                self.wide_timer = self.slow_timer = 0.0
                self.launched = False
                if self.lives == 0:
                    self.over = True
                    self.result = f'GAME OVER - SCORE {self.score}'
                else:
                    self.balls = [Ball(self.paddle, PADDLE_Y - 1, 0, 0)]
                return
            remaining = []
            for item in self.items:
                old_y = item.y
                item.y += 5 * tick
                if old_y <= PADDLE_Y <= item.y and abs(item.x - self.paddle) <= self.paddle_width / 2:
                    self.apply_item(item.kind)
                elif item.y < H:
                    remaining.append(item)
            self.items = remaining

    def draw(self, screen):
        screen.centered(0, 'B R I C K   B U R S T', 1)
        screen.text(2, 1, f'SCORE {self.score:4}  LIVES {self.lives}  BALLS {len(self.balls)}  BRICKS {len(self.bricks):2}', 2)
        screen.border(3, H + 2)
        for brick in self.bricks:
            screen.text(4 + int(brick.y), 2 + int(brick.x), '[===]', 1 + int(brick.y) % 4)
        for item in self.items:
            symbol, _, color = ITEMS[item.kind]
            screen.text(4 + int(item.y), 2 + int(item.x), symbol, color)
        for ball in self.balls:
            screen.text(4 + int(ball.y), 2 + int(ball.x), 'O', 2)
        screen.text(4 + PADDLE_Y, 2 + int(self.paddle) - self.paddle_width // 2,
                    '[' + '=' * (self.paddle_width - 2) + ']', 4)
        if not self.launched and not self.over:
            screen.centered(18, 'SPACE TO LAUNCH', 2)
        effects = []
        if self.wide_timer > 0:
            effects.append(f'WIDE {math.ceil(self.wide_timer)}s')
        if self.slow_timer > 0:
            effects.append(f'SLOW {math.ceil(self.slow_timer)}s')
        message = self.message if self.message_timer > 0 else 'Catch falling items with your paddle!'
        screen.centered(27, ' | '.join(effects) if effects else message, 2)
        screen.text(28, 1, 'LEFT/RIGHT or A/D: Move  SPACE: Launch')
        screen.text(29, 1, 'P: Pause  R: Restart  Q: Quit')
        screen.text(31, 1, 'Items: 2 = x2 balls   W = wide   S = slow   + = life')


def main():
    return run(BreakoutGame)


if __name__ == '__main__':
    raise SystemExit(main())
