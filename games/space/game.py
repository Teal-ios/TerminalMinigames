"""Star Defender: readable attack waves and terminal-friendly flight controls."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import curses
from dataclasses import dataclass, field
import math

from arcade_screen import run

W, H = 60, 22


@dataclass
class Enemy:
    x: float
    y: float
    cooldown: float = 1.0
    kind: str = 'scout'
    hp: int = 0
    age: float = 0.0
    warning: float = 0.0
    lanes: list = field(default_factory=list)
    flash: float = 0.0

    def __post_init__(self):
        self.hp = self.hp or {'scout': 1, 'weaver': 1, 'gunship': 3, 'boss': 24}[self.kind]
        self.max_hp = self.hp
        self.origin_x = self.x

    @property
    def radius(self):
        return 3 if self.kind == 'boss' else 1


class SpaceGame:
    def __init__(self):
        self.x, self.y = float(W // 2), float(H - 2)
        self.vx = self.vy = 0.0
        self.move_x = self.move_y = 0
        self.input_x = self.input_y = 0.0
        self.shots, self.hostile, self.enemies = [], [], []
        self.effects = []
        self.lives, self.score, self.bombs = 3, 0, 2
        self.elapsed = self.spawn_clock = self.cooldown = self.invincible = 0.0
        self.chain = 0
        self.chain_timer = self.bomb_flash = 0.0
        self.over, self.auto = False, True
        self.auto_delay = .35
        self.result = 'GAME OVER'
        self.start_wave(1)

    @property
    def level(self):
        return self.wave

    @property
    def multiplier(self):
        return 1 + min(2, self.chain // 5)

    def start_wave(self, number):
        self.wave = number
        self.wave_wait = 1.2
        self.spawn_clock = 0.0
        self.clear_wait = 1.6
        self.banner = f'WAVE {number:02d} - INCOMING'
        self.banner_time = 1.5
        if number % 4 == 0:
            self.queue = ['boss']
            self.banner = f'WAVE {number:02d} - BOSS APPROACHING'
        else:
            # Symmetric lanes make each wave learnable; silhouettes teach threats.
            self.queue = ['scout', 'weaver', 'scout', 'gunship', 'weaver', 'scout']
            self.queue += ['gunship', 'weaver'] * min(3, (number - 1) // 4)
        self.spawned = 0

    def fire(self):
        if not self.over and self.cooldown <= 1e-9:
            self.shots.append((self.x, self.y - 1))
            self.cooldown = .18

    def handle(self, key):
        if self.over:
            return
        if key in (curses.KEY_LEFT, ord('a'), ord('A')):
            self.move_x, self.input_x = -1, .20
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
            self.move_x, self.input_x = 1, .20
        elif key in (curses.KEY_UP, ord('w'), ord('W')):
            self.move_y, self.input_y = -1, .20
        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
            self.move_y, self.input_y = 1, .20
        elif key == ord(' '):
            self.fire()
        elif key in (ord('f'), ord('F')):
            self.auto = not self.auto
        elif key in (ord('x'), ord('X')):
            self.bomb()

    def bomb(self):
        if self.over or self.bombs <= 0:
            return
        self.bombs -= 1
        self.hostile.clear()
        self.invincible = max(self.invincible, 1.0)
        self.bomb_flash = .45
        for enemy in self.enemies[:]:
            self.damage(enemy, 6 if enemy.kind == 'boss' else enemy.hp)
            enemy.warning = 0
            enemy.lanes.clear()
            enemy.cooldown = max(enemy.cooldown, 1.0)
        self.banner, self.banner_time = 'NOVA BOMB - BULLETS CLEARED', 1.0

    def hurt(self):
        if self.invincible <= 0 and not self.over:
            self.lives -= 1
            self.invincible = 1.5
            self.chain = 0
            self.effects.append([self.x, self.y, .65, 'HIT!', 3])
            self.over = self.lives <= 0
            if self.over:
                self.result = f'GAME OVER - SCORE {self.score}'

    def damage(self, enemy, amount=1):
        enemy.hp = max(0, enemy.hp - amount)
        enemy.flash = .1
        if enemy.hp > 0:
            return
        self.enemies.remove(enemy)
        self.chain += 1
        self.chain_timer = 3.0
        points = {'scout': 100, 'weaver': 150, 'gunship': 250, 'boss': 1500}[enemy.kind]
        points *= self.multiplier
        self.score += points
        self.effects.append([enemy.x, enemy.y, .65, f'+{points}', 2])
        if enemy.kind == 'boss':
            self.hostile.clear()
            self.bombs = min(3, self.bombs + 1)
            self.banner, self.banner_time = 'BOSS DOWN! +1 NOVA BOMB', 1.5

    @staticmethod
    def approach(value, target, amount):
        return min(target, value + amount) if value < target else max(target, value - amount)

    def move(self, dt):
        dx = self.move_x if self.input_x > 1e-9 else 0
        dy = self.move_y if self.input_y > 1e-9 else 0
        self.input_x = max(0, self.input_x - dt)
        self.input_y = max(0, self.input_y - dt)
        diagonal = .7071 if dx and dy else 1.0
        self.vx = self.approach(self.vx, dx * 24 * diagonal, 110 * dt)
        self.vy = self.approach(self.vy, dy * 14 * diagonal, 80 * dt)
        self.x = max(1., min(W - 2., self.x + self.vx * dt))
        self.y = max(float(H // 2), min(H - 1., self.y + self.vy * dt))
        if self.x in (1., W - 2.):
            self.vx = 0
        if self.y in (float(H // 2), H - 1.):
            self.vy = 0

    def spawn(self, dt):
        if self.wave_wait > 0:
            self.wave_wait = max(0, self.wave_wait - dt)
            return
        if self.queue:
            self.spawn_clock -= dt
            if self.spawn_clock <= 1e-9:
                kind = self.queue.pop(0)
                x = [12, 46, 24, 36, 18, 42, 8, 52][self.spawned % 8]
                hp = 24 + 4 * min(6, self.wave // 4 - 1) if kind == 'boss' else 0
                self.enemies.append(Enemy(30 if kind == 'boss' else x, 0,
                                          1.3, kind=kind, hp=hp))
                self.spawned += 1
                self.spawn_clock = .55
        elif not self.enemies:
            self.clear_wait -= dt
            if self.clear_wait <= 0:
                self.start_wave(self.wave + 1)
            elif self.banner_time <= 0:
                self.banner, self.banner_time = f'WAVE {self.wave:02d} CLEAR', self.clear_wait

    def enemy_fire(self, enemy, dt):
        if enemy.warning > 0:
            enemy.warning = max(0, enemy.warning - dt)
            if enemy.warning <= 1e-9:
                self.hostile.extend((lane, enemy.y + 1) for lane in enemy.lanes)
                enemy.lanes.clear()
                enemy.cooldown = (1.1 if enemy.hp <= enemy.max_hp / 2 else 1.7) if enemy.kind == 'boss' else 2.0
            return
        enemy.cooldown -= dt
        # No bullets appear below the player's upper movement limit.
        if enemy.cooldown > 0 or enemy.y < 1 or enemy.y >= H // 2 - 2:
            return
        if enemy.kind == 'boss':
            enemy.lanes = [max(2., min(W - 3., self.x)) + offset for offset in (-12, -6, 0, 6, 12)]
            enemy.warning = .8
        elif enemy.kind == 'gunship':
            enemy.lanes = [enemy.x - 3, enemy.x, enemy.x + 3]
            enemy.warning = .6
        else:
            enemy.lanes = [enemy.x]
            enemy.warning = .55
        enemy.lanes = [x for x in enemy.lanes if 1 <= x <= W - 2]

    def update(self, dt):
        if self.over or dt <= 0 or not math.isfinite(dt):
            return
        # Full elapsed time is simulated. Small slices bound motion relative to
        # ship hitboxes, so low frame rates cannot tunnel through targets.
        remaining = dt
        while remaining > 1e-9 and not self.over:
            step = min(.01, remaining)
            self.step(step)
            remaining -= step

    def step(self, dt):
        self.elapsed += dt
        self.cooldown = max(0, self.cooldown - dt)
        self.auto_delay = max(0, self.auto_delay - dt)
        self.invincible = max(0, self.invincible - dt)
        self.banner_time = max(0, self.banner_time - dt)
        self.bomb_flash = max(0, self.bomb_flash - dt)
        self.chain_timer = max(0, self.chain_timer - dt)
        if self.chain_timer <= 0:
            self.chain = 0
        self.move(dt)
        if self.auto and self.auto_delay <= 0:
            self.fire()
        self.spawn(dt)
        for effect in self.effects:
            effect[2] -= dt
        self.effects = [effect for effect in self.effects if effect[2] > 0]
        for enemy in self.enemies[:]:
            enemy.age += dt
            enemy.flash = max(0, enemy.flash - dt)
            speed = min(2.8, 1.4 + self.wave * .10)
            if enemy.kind == 'boss':
                enemy.y = min(3., enemy.y + 4 * dt)
                enemy.x = 30 + 17 * math.sin(enemy.age * .55)
            else:
                enemy.y += speed * {'scout': 1.3, 'weaver': 1.0, 'gunship': .65}[enemy.kind] * dt
                if enemy.kind == 'weaver':
                    enemy.x = max(2., min(W - 3., enemy.origin_x + 7 * math.sin(enemy.age * 1.5)))
            self.enemy_fire(enemy, dt)
            if abs(enemy.x - self.x) <= enemy.radius + .6 and abs(enemy.y - self.y) <= .8:
                self.hurt()
                if enemy.kind != 'boss':
                    self.enemies.remove(enemy)
            elif enemy.y >= H:
                self.enemies.remove(enemy)
                self.chain = 0
        shots = []
        for x, y in self.shots:
            next_y = y - 26 * dt
            targets = [enemy for enemy in self.enemies
                       if abs(enemy.x - x) <= enemy.radius
                       and next_y - .6 <= enemy.y <= y + .6]
            if targets:
                self.damage(max(targets, key=lambda enemy: enemy.y))
            elif next_y >= 0:
                shots.append((x, next_y))
        self.shots = shots
        hostile = []
        for x, y in self.hostile:
            next_y = y + min(10, 7 + self.wave * .15) * dt
            if abs(x - self.x) <= .65 and y <= self.y + .6 and next_y >= self.y - .6:
                self.hurt()
            elif next_y < H:
                hostile.append((x, next_y))
        self.hostile = hostile

    def draw(self, screen):
        screen.centered(0, 'S T A R   D E F E N D E R', 1)
        screen.text(1, 2, f'SCORE {self.score:07d}  SHIPS {self.lives}  WAVE {self.wave:02d}', 2)
        screen.text(2, 2, f'AUTO {"ON " if self.auto else "OFF"}  NOVA {self.bombs}  CHAIN {self.chain:02d}  x{self.multiplier}', 4)
        screen.border(3, H + 2)
        for index in range(24):
            x = (index * 17 + 5) % W
            y = (index * 7 + int(self.elapsed * (1 + index % 2))) % H
            screen.text(4 + y, 2 + x, '.' if index % 3 else ':', 7)
        for enemy in self.enemies:
            if enemy.warning > 0:
                for lane in enemy.lanes:
                    if enemy.kind == 'boss':
                        for y in range(int(enemy.y) + 2, H, 2):
                            screen.text(4 + y, 2 + round(lane), ':', 6)
                    screen.text(4 + min(H - 1, int(enemy.y) + 1), 2 + round(lane), '!', 2)
        for x, y in self.shots:
            screen.text(4 + int(y), 2 + round(x), '|', 4)
            if y + 1 < H:
                screen.text(5 + int(y), 2 + round(x), ':', 7)
        sprites = {'scout': ('\\V/', 3), 'weaver': ('<~>', 6),
                   'gunship': ('[M]', 2), 'boss': ('<=[W]=>', 3)}
        for enemy in self.enemies:
            sprite, color = sprites[enemy.kind]
            screen.text(4 + int(enemy.y), 2 + round(enemy.x) - len(sprite) // 2,
                        sprite, 8 if enemy.flash else color)
        for x, y in self.hostile:
            screen.text(4 + int(y), 2 + round(x), 'o', 2)
        for x, y, life, label, color in self.effects:
            text = '*+*' if life > .4 else label
            screen.text(4 + max(0, min(H - 1, int(y))),
                        max(2, min(W + 1 - len(text), round(x))), text, color)
        if self.invincible <= 0 or int(self.elapsed * 12) % 2 == 0:
            screen.text(4 + round(self.y), 1 + round(self.x), '/A\\', 1)
            if round(self.y) + 1 < H:
                screen.text(5 + round(self.y), 2 + round(self.x), '^', 4)
        if self.bomb_flash > 0:
            screen.centered(15, '* * *  N O V A  * * *', 8)
        if self.banner_time > 0:
            screen.centered(7, f' {self.banner} ', 2)
        boss = next((enemy for enemy in self.enemies if enemy.kind == 'boss'), None)
        if boss:
            bars = math.ceil(20 * boss.hp / boss.max_hp)
            screen.centered(27, f'BOSS [{"#" * bars}{"." * (20 - bars)}] {boss.hp:02d}', 3)
        else:
            screen.centered(27, r'\V/ SCOUT   <~> WEAVER   [M] ARMOURED (3 HITS)', 7)
        screen.text(28, 1, 'ARROWS/WASD: Move  SPACE: Fire  F: Auto  X: Nova bomb')
        screen.text(29, 1, 'P: Pause  R: Restart  Q: Quit')
        screen.text(31, 1, 'Avoid marked lanes. Escapes break chain; boss gives +1 bomb.')


def main():
    return run(SpaceGame)


if __name__ == '__main__':
    raise SystemExit(main())
