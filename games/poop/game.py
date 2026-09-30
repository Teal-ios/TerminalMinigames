"""Telegraphed terminal survival with near misses and a cooldown dash."""
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import curses
from dataclasses import dataclass
import math
import random

from arcade_screen import run

WIDTH, HEIGHT = 60, 22


@dataclass
class Drop:
    x: float
    y: float
    speed: float
    heavy: bool = False


@dataclass
class Warning:
    x: float
    remaining: float = .55
    heavy: bool = False


class Game:
    def __init__(self, rng=None, best=0):
        self.rng = rng if rng is not None else random.Random()
        self.player = WIDTH / 2
        self.vx = self.direction = self.move_timer = 0
        self.last_direction = 1
        self.drops, self.warnings, self.effects = [], [], []
        self.elapsed = self.spawn_clock = self.invincible = 0.0
        self.dash_timer = self.dash_cooldown = 0.0
        self.lives, self.bonus, self.near_misses, self.best = 3, 0, 0, best
        self.spawn_count = 0
        self.over = False
        self.result = ''
        self.message, self.message_timer = 'Watch the warning lanes. Keep an escape route.', 2.5

    @property
    def score(self):
        return int(self.elapsed * 10) + self.bonus

    @property
    def level(self):
        return 1 + int(self.elapsed // 15)

    def restart(self):
        return type(self)(best=max(self.best, self.score))

    def move(self, direction):
        if not self.over:
            self.direction = self.last_direction = -1 if direction < 0 else 1
            self.move_timer = .26

    def handle(self, key):
        if key in (curses.KEY_LEFT, ord('a'), ord('A')):
            self.move(-1)
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
            self.move(1)
        elif key == ord(' ') and self.dash_cooldown <= 0 and not self.over:
            self.dash_timer, self.dash_cooldown = .18, 2.5
            self.invincible = max(self.invincible, .22)
            self.message, self.message_timer = 'DASH!', .45

    def hurt(self):
        if self.invincible > 0 or self.over:
            return
        self.lives -= 1
        self.invincible = 1.2
        self.effects.append([self.player, HEIGHT - 1, .45, 3])
        self.message, self.message_timer = 'SPLAT! Find a clear lane.', 1.0
        if self.lives <= 0:
            self.over = True
            self.result = f'RUN OVER - SCORE {self.score} - R TO RETRY'

    def schedule_drop(self):
        self.spawn_count += 1
        center = self.rng.randrange(2, WIDTH - 2)
        lanes = [center]
        # Sparse showers retain a wide visible escape route, never a solid wall.
        if self.level >= 3 and self.spawn_count % 6 == 0:
            lanes = [max(2, min(WIDTH - 3, center + offset)) for offset in (-6, 0, 6)]
        for x in sorted(set(lanes)):
            self.warnings.append(Warning(x, heavy=self.level >= 2 and self.spawn_count % 4 == 0))

    def update(self, dt):
        if self.over:
            return
        steps = max(1, math.ceil(dt / .02))
        for _ in range(steps):
            if self.over:
                break
            self.tick(dt / steps)
        self.best = max(self.best, self.score)

    def tick(self, dt):
        self.elapsed += dt
        for name in ('invincible', 'dash_cooldown', 'move_timer', 'message_timer'):
            setattr(self, name, max(0, getattr(self, name) - dt))
        if self.dash_timer > 0:
            self.dash_timer = max(0, self.dash_timer - dt)
            self.vx = self.last_direction * 42
        else:
            target = self.direction * 22 if self.move_timer > 0 else 0
            self.vx += max(-180 * dt, min(180 * dt, target - self.vx))
        previous_player = self.player
        self.player = max(1, min(WIDTH - 2, self.player + self.vx * dt))
        for effect in self.effects:
            effect[2] -= dt
        self.effects = [effect for effect in self.effects if effect[2] > 0]
        for warning in list(self.warnings):
            warning.remaining -= dt
            if warning.remaining <= 0:
                speed = min(16, 5 + self.level * .8) * (1.2 if warning.heavy else 1)
                self.drops.append(Drop(warning.x, 0, speed, warning.heavy))
                self.warnings.remove(warning)
        remaining = []
        for drop in sorted(self.drops, key=lambda d: (HEIGHT - 1 - d.y) / d.speed):
            previous = drop.y
            drop.y += drop.speed * dt
            if previous < HEIGHT - 1 <= drop.y:
                crossing = (HEIGHT - 1 - previous) / (drop.y - previous)
                contact_x = previous_player + (self.player - previous_player) * crossing
                distance = abs(drop.x - contact_x)
                radius = 1.4 if drop.heavy else .8
                if distance <= radius:
                    self.hurt()
                    if self.over:
                        break
                else:
                    self.bonus += 5
                    if distance <= radius + 1.8:
                        self.near_misses += 1
                        self.bonus += 25
                        self.message, self.message_timer = 'CLOSE CALL! +25', .8
                        self.effects.append([drop.x, HEIGHT - 1, .35, 2])
                self.effects.append([drop.x, HEIGHT - 1, .25, 7])
            elif drop.y < HEIGHT:
                remaining.append(drop)
        self.drops = remaining
        if self.over:
            return
        self.spawn_clock += dt
        interval = max(.16, .65 - (self.level - 1) * .055)
        while self.spawn_clock >= interval:
            self.spawn_clock -= interval
            self.schedule_drop()

    def draw(self, screen):
        screen.centered(0, 'P O O P   D O D G E  /  RAIN RUN', 1)
        screen.text(2, 1, f'SCORE {self.score:6}  BEST {self.best:6}  HP {"o" * self.lives:<3}  LV {self.level}', 2)
        screen.border(3, HEIGHT + 2)
        for x in range(0, WIDTH, 4):
            screen.text(4 + HEIGHT - 1, 2 + x, '_', 7)
        for warning in self.warnings:
            screen.text(4, 2 + round(warning.x), '!' if warning.heavy else 'v', 3 if warning.heavy else 2)
            if int(warning.remaining * 12) % 2 == 0:
                screen.text(4 + HEIGHT - 2, 2 + round(warning.x), ':', 7)
        for drop in self.drops:
            row, col = 4 + int(drop.y), 2 + int(drop.x)
            if drop.y >= 1:
                screen.text(row - 1, col, ':', 7)
            screen.text(row, col - (1 if drop.heavy else 0), '(#)' if drop.heavy else '*', 3 if drop.heavy else 2)
        for x, y, ttl, color in self.effects:
            screen.text(4 + int(y), max(1, min(59, 1 + round(x))), '*.*' if ttl > .15 else '.', color)
        if self.invincible <= 0 or int(self.elapsed * 14) % 2 == 0:
            x = round(self.player)
            screen.text(4 + HEIGHT - 2, 2 + x, 'o', 1)
            screen.text(4 + HEIGHT - 1, 1 + x, '/|\\', 1)
            if self.dash_timer > 0:
                tail = max(1, min(58, x - self.last_direction * 3))
                screen.text(4 + HEIGHT - 1, tail, '~~', 4)
        dash = 'READY' if self.dash_cooldown <= 0 else f'{self.dash_cooldown:.1f}s'
        screen.text(27, 1, f'DASH {dash:<5}  CLOSE CALLS {self.near_misses}   SURVIVED {self.elapsed:5.1f}s', 4)
        screen.centered(28, self.message if self.message_timer > 0 else 'v = incoming drop   ! = heavy drop', 2)
        screen.text(29, 1, 'A/D or ARROWS: Move  SPACE: Dash  P: Pause')
        screen.text(31, 1, '3 hearts / near miss +25 / R: Retry / Q: Quit', 1)


def main():
    return run(Game)


if __name__ == '__main__':
    raise SystemExit(main())
