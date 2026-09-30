"""Three-stage terminal brick breaker with swept collision and aimed serves."""
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import curses
from dataclasses import dataclass, field
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
STAGE_NAMES = ('OPENING GATES', 'DIAMOND MINE', 'REACTOR CORE')


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    trail: list = field(default_factory=list)
    trail_clock: float = 0


@dataclass
class Brick:
    x: float
    y: float
    width: int = 5
    hp: int = 1
    kind: str = 'normal'


@dataclass
class Item:
    x: float
    y: float
    kind: str


class BreakoutGame:
    def __init__(self, rng=None):
        self.rng = rng if rng is not None else random.Random()
        self.paddle = W / 2
        self.paddle_vx = self.move_timer = 0.0
        self.move_dir = 0
        self.aim = 18
        self.lives, self.score, self.stage, self.combo = 3, 0, 1, 0
        self.stage_pause = 0.0
        self.items, self.particles = [], []
        self.wide_timer = self.slow_timer = self.message_timer = 0.0
        self.message = ''
        self.launched = self.over = False
        self.result = ''
        self.build_stage()
        self.serve()

    def build_stage(self):
        self.bricks = []
        for row in range(5):
            for col in range(10):
                if self.stage == 1 and (row == 4 or col in (4, 5) and row in (1, 2)):
                    continue
                if self.stage == 2 and abs(col - 4.5) + abs(row - 2) > 4.5:
                    continue
                if self.stage == 3 and row in (1, 3) and col in (2, 7):
                    continue
                reinforced = (self.stage == 1 and row == 0 and col in (2, 7)
                              or self.stage == 2 and (row + col) % 4 == 0
                              or self.stage == 3 and (row == 0 or col in (0, 9)))
                explosive = (row == 2 and col in (2, 7) if self.stage == 1 else
                             (row, col) in ((1, 4), (3, 5)) if self.stage == 2 else
                             row == 2 and col in (1, 4, 5, 8))
                self.bricks.append(Brick(6 * col + 1, row * 2 + 2, hp=2 if reinforced else 1,
                                         kind='explosive' if explosive else 'normal'))

    def serve(self):
        self.launched = False
        self.combo = 0
        self.paddle_vx = self.move_timer = 0
        self.wide_timer = self.slow_timer = 0
        self.items.clear()
        self.clamp_paddle()
        self.balls = [Ball(self.paddle, PADDLE_Y - 1, 0, 0)]

    @property
    def paddle_width(self):
        return 15 if self.wide_timer > 0 else 9

    def clamp_paddle(self):
        half = self.paddle_width // 2
        limited = max(half, min(W - 1 - half, self.paddle))
        if limited != self.paddle:
            self.paddle_vx = 0
        self.paddle = limited

    def handle(self, key):
        if self.over or self.stage_pause > 0:
            return
        if key in (curses.KEY_LEFT, ord('a'), ord('A'), curses.KEY_RIGHT, ord('d'), ord('D')):
            self.move_dir = -1 if key in (curses.KEY_LEFT, ord('a'), ord('A')) else 1
            self.move_timer = .26
        elif not self.launched and key in (ord('j'), ord('J'), ord('l'), ord('L')):
            self.aim = max(-60, min(60, self.aim + (-6 if key in (ord('j'), ord('J')) else 6)))
        elif key in (ord(' '), 10, 13) and not self.launched:
            self.launched = True
            angle = math.radians(self.aim)
            self.balls[0].vx, self.balls[0].vy = 13 * math.sin(angle), -13 * math.cos(angle)

    def burst(self, x, y, color=2):
        # Cosmetic effects never consume the gameplay RNG used for item drops.
        for index in range(6):
            angle = index * math.pi / 3
            self.particles.append([x, y, math.cos(angle) * 7, math.sin(angle) * 4, .35, color])
        self.particles = self.particles[-120:]

    def damage_brick(self, brick):
        if brick not in self.bricks:
            return
        brick.hp -= 1
        self.burst(brick.x + brick.width / 2, brick.y, 3 if brick.kind == 'explosive' else 2)
        if brick.hp > 0:
            return
        self.bricks.remove(brick)
        self.combo += 1
        self.score += 10 * min(5, self.combo)
        if self.rng.random() < .30:
            self.items.append(Item(brick.x + brick.width // 2, brick.y + 1,
                                   self.rng.choice(tuple(ITEMS))))
        if brick.kind == 'explosive':
            for neighbor in list(self.bricks):
                if abs(neighbor.x - brick.x) <= 6 and abs(neighbor.y - brick.y) <= 2:
                    self.damage_brick(neighbor)

    def apply_item(self, kind):
        self.message = ITEMS[kind][1]
        self.message_timer = 2.5
        if kind == 'double':
            for index, ball in enumerate(list(self.balls)):
                if len(self.balls) >= MAX_BALLS:
                    break
                angle = math.radians(28 if index % 2 == 0 else -28)
                vx = ball.vx * math.cos(angle) - ball.vy * math.sin(angle)
                vy = ball.vx * math.sin(angle) + ball.vy * math.cos(angle)
                speed = math.hypot(ball.vx, ball.vy)
                if abs(vy) < speed * .35:
                    vy = math.copysign(speed * .35, ball.vy or -1)
                    vx = math.copysign(math.sqrt(max(0, speed * speed - vy * vy)), vx)
                self.balls.append(Ball(ball.x, ball.y, vx, vy))
        elif kind == 'wide':
            self.wide_timer = 12.0
            self.clamp_paddle()
        elif kind == 'slow':
            self.slow_timer = 8.0
        elif kind == 'life':
            self.lives = min(5, self.lives + 1)

    @staticmethod
    def brick_contact(ball, brick, dt):
        """Ray/slab intersection returns entry time and the contacted axis."""
        entry, leave, axis = -math.inf, math.inf, 0
        for index, (position, velocity, low, high) in enumerate((
                (ball.x, ball.vx, brick.x - .85, brick.x + brick.width - .15),
                (ball.y, ball.vy, brick.y - .85, brick.y + .85))):
            if abs(velocity) < 1e-9:
                if not low <= position <= high:
                    return None
                continue
            first, last = sorted(((low - position) / velocity, (high - position) / velocity))
            if first > entry:
                entry, axis = first, index
            leave = min(leave, last)
        if entry < -1e-8 or entry > leave or entry > dt:
            return None
        return max(0, entry), axis

    def advance_ball(self, ball, dt):
        """Resolve the earliest contact, then sweep the unused part of the step."""
        remaining = dt
        for _ in range(32):
            if remaining <= 1e-8:
                break
            contacts = []
            if ball.vx < 0:
                contacts.append(((0 - ball.x) / ball.vx, 'wall', 0))
            elif ball.vx > 0:
                contacts.append(((W - 1 - ball.x) / ball.vx, 'wall', 0))
            if ball.vy < 0:
                contacts.append((-ball.y / ball.vy, 'wall', 1))
            elif ball.vy > 0 and ball.y <= PADDLE_Y - .5:
                when = (PADDLE_Y - .5 - ball.y) / ball.vy
                if abs(ball.x + ball.vx * when - self.paddle) <= self.paddle_width / 2:
                    contacts.append((when, 'paddle', 1))
            for brick in self.bricks:
                contact = self.brick_contact(ball, brick, remaining)
                if contact is not None:
                    contacts.append((contact[0], brick, contact[1]))
            valid = [contact for contact in contacts if -1e-8 <= contact[0] <= remaining]
            if not valid:
                ball.x += ball.vx * remaining
                ball.y += ball.vy * remaining
                break
            when, target, axis = min(valid, key=lambda contact: contact[0])
            when = max(0, when)
            ball.x += ball.vx * when
            ball.y += ball.vy * when
            remaining -= when
            if target == 'paddle':
                offset = max(-1, min(1, (ball.x - self.paddle) / (self.paddle_width / 2)))
                angle = offset * math.radians(62)
                speed = max(13, math.hypot(ball.vx, ball.vy))
                ball.vx, ball.vy = math.sin(angle) * speed, -math.cos(angle) * speed
                self.combo = 0
                self.burst(ball.x, ball.y, 4)
            else:
                if axis == 0:
                    ball.vx = -ball.vx
                else:
                    ball.vy = -ball.vy
                if isinstance(target, Brick):
                    self.damage_brick(target)
            # Move a tiny distance away from the contact plane to avoid double hits.
            epsilon = min(remaining, 1e-7)
            ball.x += ball.vx * epsilon
            ball.y += ball.vy * epsilon
            remaining -= epsilon

    def update(self, dt):
        if self.over:
            return
        steps = max(1, math.ceil(dt / .01))
        for _ in range(steps):
            self.tick(dt / steps)
            if self.over:
                break

    def tick(self, dt):
        self.message_timer = max(0, self.message_timer - dt)
        for particle in self.particles:
            particle[0] += particle[2] * dt
            particle[1] += particle[3] * dt
            particle[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        if self.stage_pause > 0:
            self.stage_pause = max(0, self.stage_pause - dt)
            if self.stage_pause == 0:
                self.stage += 1
                self.build_stage()
                self.serve()
            return
        self.wide_timer = max(0, self.wide_timer - dt)
        self.slow_timer = max(0, self.slow_timer - dt)
        target = self.move_dir * 40 if self.move_timer > 0 else 0
        self.move_timer = max(0, self.move_timer - dt)
        self.paddle_vx += max(-220 * dt, min(220 * dt, target - self.paddle_vx))
        self.paddle += self.paddle_vx * dt
        self.clamp_paddle()
        if not self.launched:
            self.balls[0].x = self.paddle
            return
        for ball in list(self.balls):
            ball.trail = [(x, y, age + dt) for x, y, age in ball.trail if age + dt < .18]
            ball.trail_clock -= dt
            if ball.trail_clock <= 0:
                ball.trail.append((ball.x, ball.y, 0))
                ball.trail_clock = .035
            self.advance_ball(ball, dt * (.65 if self.slow_timer > 0 else 1))
        self.balls = [ball for ball in self.balls if ball.y < H]
        if not self.bricks:
            if self.stage == 3:
                self.over = True
                self.result = f'ALL 3 STAGES CLEAR! SCORE {self.score}'
            else:
                self.stage_pause = 1.2
                self.launched = False
                self.message, self.message_timer = f'STAGE {self.stage} CLEAR!', 1.2
                self.items.clear()
            return
        if not self.balls:
            self.lives -= 1
            if self.lives <= 0:
                self.over = True
                self.result = f'GAME OVER - SCORE {self.score}'
            else:
                self.serve()
            return
        remaining = []
        for item in self.items:
            old_y = item.y
            item.y += 5 * dt
            if old_y <= PADDLE_Y <= item.y and abs(item.x - self.paddle) <= self.paddle_width / 2:
                self.apply_item(item.kind)
            elif item.y < H:
                remaining.append(item)
        self.items = remaining

    def draw(self, screen):
        screen.centered(0, 'B R I C K   B U R S T', 1)
        screen.text(1, 2, f'STAGE {self.stage}/3  {STAGE_NAMES[self.stage - 1]}', 7)
        screen.text(2, 1, f'SCORE {self.score:5}  LIVES {self.lives}  BALLS {len(self.balls)}  CHAIN x{min(5, self.combo):1}', 2)
        screen.border(3, H + 2)

        def dot(x, y, value, color=7):
            if 0 <= x < W and 0 <= y < H:
                screen.text(4 + int(y), 2 + int(x), value, color)

        for brick in self.bricks:
            shape = '[***]' if brick.kind == 'explosive' else '[#2#]' if brick.hp > 1 else '[===]'
            dot(brick.x, brick.y, shape, 3 if brick.kind == 'explosive' else 2 if brick.hp > 1 else 1 + int(brick.y) % 4)
        for ball in self.balls:
            for x, y, age in ball.trail:
                dot(x, y, '.', 7)
        for x, y, vx, vy, ttl, color in self.particles:
            dot(x, y, '+' if ttl > .18 else '.', color)
        for item in self.items:
            symbol, _, color = ITEMS[item.kind]
            dot(item.x, item.y, symbol, color)
        if not self.launched and not self.stage_pause:
            angle = math.radians(self.aim)
            for distance in range(2, 8):
                dot(self.paddle + math.sin(angle) * distance, PADDLE_Y - 1 - math.cos(angle) * distance, ':', 1)
            screen.centered(16, f'J/L AIM {self.aim:+3}  SPACE TO LAUNCH', 2)
        for ball in self.balls:
            dot(ball.x, ball.y, 'O', 2)
        dot(self.paddle - self.paddle_width // 2, PADDLE_Y,
            '[' + '=' * (self.paddle_width - 2) + ']', 4)
        if self.stage_pause:
            screen.centered(15, f'STAGE {self.stage} CLEAR! NEXT STAGE...', 2)
        effects = []
        if self.wide_timer > 0:
            effects.append(f'WIDE {math.ceil(self.wide_timer)}s')
        if self.slow_timer > 0:
            effects.append(f'SLOW {math.ceil(self.slow_timer)}s')
        screen.centered(27, ' | '.join(effects) if effects else self.message if self.message_timer > 0
                        else '[#2#] 2 hits  [***] blast  Chain resets at paddle', 2)
        screen.text(28, 1, 'ARROWS/A/D: Move  J/L: Aim serve  SPACE: Launch')
        screen.text(29, 1, 'P: Pause  R: Restart  Q: Quit')
        screen.text(31, 1, 'Items: 2 = x2 balls   W = wide   S = slow   + = life')


def main():
    return run(BreakoutGame)


if __name__ == '__main__':
    raise SystemExit(main())
