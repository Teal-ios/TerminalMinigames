"""Terminal space shooter rules and display."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import curses
from dataclasses import dataclass
import random

from arcade_screen import run

W, H = 60, 22


@dataclass
class Enemy:
    x: float
    y: float
    cooldown: float = 1.0


class SpaceGame:
    def __init__(self):
        self.x, self.y = W // 2, H - 2
        self.shots, self.hostile, self.enemies = [], [], []
        self.lives, self.score = 3, 0
        self.elapsed = self.spawn_clock = self.cooldown = self.invincible = 0.0
        self.over, self.auto = False, False
        self.result = 'GAME OVER'

    @property
    def level(self):
        return 1 + self.score // 500

    def fire(self):
        if self.cooldown <= 0:
            self.shots.append((self.x, self.y - 1))
            self.cooldown = 0.18

    def handle(self, key):
        if key in (curses.KEY_LEFT, ord('a'), ord('A')):
            self.x = max(1, self.x - 1)
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
            self.x = min(W - 2, self.x + 1)
        elif key in (curses.KEY_UP, ord('w'), ord('W')):
            self.y = max(H // 2, self.y - 1)
        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
            self.y = min(H - 1, self.y + 1)
        elif key == ord(' '):
            self.fire()
        elif key in (ord('f'), ord('F')):
            self.auto = not self.auto

    def hurt(self):
        if self.invincible <= 0:
            self.lives -= 1
            self.invincible = 1.5
            self.over = self.lives <= 0
            if self.over:
                self.result = f'GAME OVER - SCORE {self.score}'

    def update(self, dt):
        if self.over:
            return
        self.elapsed += dt
        self.cooldown = max(0, self.cooldown - dt)
        self.invincible = max(0, self.invincible - dt)
        if self.auto:
            self.fire()
        self.spawn_clock += dt
        interval = max(0.25, 1.0 - (self.level - 1) * 0.08)
        while self.spawn_clock >= interval:
            self.spawn_clock -= interval
            self.enemies.append(Enemy(random.randrange(2, W - 2), 0,
                                      random.uniform(0.6, 1.8)))
        speed = min(6, 1.3 + self.level * 0.3)
        remaining = []
        for enemy in self.enemies:
            old_y = enemy.y
            enemy.y += speed * dt
            enemy.cooldown -= dt
            if enemy.cooldown <= 0:
                self.hostile.append((enemy.x, enemy.y + 1))
                enemy.cooldown = random.uniform(1, 2.5)
            if abs(enemy.x - self.x) <= 1 and old_y <= self.y + 1 and enemy.y >= self.y - 1:
                self.hurt()
            elif enemy.y >= H:
                self.hurt()
            else:
                remaining.append(enemy)
        self.enemies = remaining
        shots = []
        for x, y in self.shots:
            next_y = y - 22 * dt
            target = next((enemy for enemy in reversed(self.enemies)
                           if abs(enemy.x - x) <= 1 and next_y - 0.6 <= enemy.y <= y + 0.6), None)
            if target is not None:
                self.enemies.remove(target)
                self.score += 100
            elif next_y >= 0:
                shots.append((x, next_y))
        self.shots = shots
        hostile = []
        for x, y in self.hostile:
            next_y = y + min(13, 6 + self.level * 0.5) * dt
            if abs(x - self.x) <= 1 and y <= self.y + 0.6 and next_y >= self.y - 0.6:
                self.hurt()
            elif next_y < H:
                hostile.append((x, next_y))
        self.hostile = hostile

    def draw(self, screen):
        screen.centered(0, 'S T A R   D E F E N D E R', 1)
        screen.text(2, 1, f'SCORE {self.score:6}   LIVES {self.lives}   LV {self.level}   AUTO {"ON" if self.auto else "OFF"}', 2)
        screen.border(3, H + 2)
        for index in range(18):
            x = (index * 17 + 5) % W
            y = (index * 7 + int(self.elapsed * 2)) % H
            screen.text(4 + y, 2 + x, '.')
        for x, y in self.shots:
            screen.text(4 + int(y), 2 + int(x), '|', 4)
        for enemy in self.enemies:
            screen.text(4 + int(enemy.y), 1 + int(enemy.x), '\\V/', 3)
        for x, y in self.hostile:
            screen.text(4 + int(y), 2 + int(x), 'o', 2)
        if self.invincible <= 0 or int(self.elapsed * 12) % 2 == 0:
            screen.text(4 + self.y, 1 + self.x, '/A\\', 1)
        screen.text(28, 1, 'ARROWS/WASD: Move  SPACE: Fire  F: Toggle auto-fire')
        screen.text(29, 1, 'P: Pause  R: Restart  Q: Quit')
        screen.text(31, 1, 'Dodge enemy fire. Escaping enemies also cost a life.')


def main():
    return run(SpaceGame)


if __name__ == '__main__':
    raise SystemExit(main())
