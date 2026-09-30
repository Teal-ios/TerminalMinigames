"""Deterministic combat rules, buffered strings, throws, meter, and CPU."""
from collections import deque
from dataclasses import dataclass, field
import math
import random

from .moves import AIR_KICK, BASIC, CHAINS, ROSTER, SWEEP, Move, Profile


@dataclass
class Attack:
    move: Move
    elapsed: float = 0.0
    resolved: int = 0
    confirmed: bool = False


@dataclass
class Fighter:
    profile: Profile
    x: float
    hp: int = 0
    y: float = 0
    vy: float = 0
    meter: float = 0
    facing: int = 1
    stun: float = 0
    down: float = 0
    guard: float = 0
    crouch: float = 0
    dash: float = 0
    invincible: float = 0
    attack: object = None
    queue: deque = field(default_factory=deque)
    history: deque = field(default_factory=lambda: deque(maxlen=3))
    last_move: str = ''
    combo_hits: int = 0
    combo_damage: int = 0
    combo_timer: float = 0

    def __post_init__(self):
        self.hp = self.profile.hp

    @property
    def free(self):
        return self.stun <= 0 and self.down <= 0


@dataclass
class Throw:
    owner: int
    move: Move
    remaining: float = 0.30
    elapsed: float = 0
    cpu_break: bool = False


@dataclass
class Projectile:
    owner: int
    x: float
    y: float
    vx: float
    move: Move


class FightGame:
    def __init__(self, selected=0, rng=None, cpu_enabled=True, cpu_selected=None):
        self.selected = selected
        self.rng = rng if rng is not None else random.Random()
        self.cpu_enabled = cpu_enabled
        self.cpu_selected = cpu_selected
        self.opponent = cpu_selected if cpu_selected is not None else self.rng.randrange(3)
        self.phase = 'select'
        self.over = False
        self.result = ''
        self.wins = [0, 0]
        self.round = 1
        self.elapsed = 0.0
        self.between = 0.0
        self.new_round()

    def new_round(self):
        previous = getattr(self, 'fighters', [])
        self.fighters = [Fighter(ROSTER[self.selected], 18),
                         Fighter(ROSTER[self.opponent], 43, facing=-1)]
        for old, new in zip(previous, self.fighters):
            new.meter = old.meter
        self.remaining = 60.0
        self.throw = None
        self.projectiles = []
        self.cpu_clock = 0.35
        self.message = 'FIGHT!'
        self.message_timer = 1.0

    def handle_menu(self, key):
        if self.phase != 'select':
            return
        if key in (ord('1'), ord('2'), ord('3')):
            self.selected = key - ord('1')
            self.new_round()
        elif key in (ord('4'), ord('5'), ord('6')):
            self.cpu_selected = key - ord('4')
            self.opponent = self.cpu_selected
            self.new_round()
        elif key == ord('0'):
            self.cpu_selected = None

    def start(self):
        self.opponent = self.cpu_selected if self.cpu_selected is not None else self.rng.randrange(3)
        self.new_round()
        self.phase = 'fight'

    def restart(self):
        return type(self)(self.selected, cpu_enabled=self.cpu_enabled, cpu_selected=self.cpu_selected)

    def say(self, text):
        self.message, self.message_timer = text, 1.1

    def press(self, side, action):
        if self.phase != 'fight' or self.over:
            return
        fighter = self.fighters[side]
        if self.throw is not None:
            if action == 'g' and side != self.throw.owner:
                self.throw = None
                for person in self.fighters:
                    person.stun = 0.18
                self.say('THROW BREAK!')
            return
        if not fighter.free:
            return
        if action in BASIC or action in fighter.profile.skills:
            if len(fighter.queue) < 3:
                fighter.queue.append((action, self.elapsed))
            self.process_queue(side)
            return
        if fighter.attack is not None:
            return
        if action in ('a', 'd'):
            fighter.x += (-1 if action == 'a' else 1) * 1.5 * fighter.profile.speed
            fighter.guard = 0
            self.boundaries()
        elif action == 'w' and fighter.y == 0:
            fighter.vy = 16
            fighter.crouch = fighter.guard = 0
        elif action == 's' and fighter.y == 0:
            fighter.crouch = 0.6
        elif action == 'guard' and fighter.y == 0:
            fighter.guard = 0.7
        elif action == 'e' and fighter.y == 0:
            fighter.dash = 0.18
            fighter.guard = 0

    def process_queue(self, side):
        fighter = self.fighters[side]
        while fighter.queue and self.elapsed - fighter.queue[0][1] > 0.75:
            fighter.queue.popleft()
        if not fighter.free or not fighter.queue or self.throw is not None:
            return
        attack = fighter.attack
        if attack is not None and not (attack.confirmed and attack.elapsed >= attack.move.last_hit + 0.06):
            return
        action, _ = fighter.queue.popleft()
        history = [item for item in fighter.history if self.elapsed - item[1] <= 1.4]
        sequence = ''.join(item[0] for item in history[-2:]) + action
        move = fighter.profile.skills.get(action, BASIC.get(action))
        if sequence in CHAINS:
            move = CHAINS[sequence]
        elif action == 'l' and fighter.y > 0:
            move = AIR_KICK
        elif action == 'l' and fighter.crouch > 0:
            move = SWEEP
        if move.cost > fighter.meter:
            if side == 0:
                self.say(f'NEED {move.cost} METER FOR {move.name}')
            return
        fighter.meter -= move.cost
        fighter.history.append((action, self.elapsed))
        fighter.attack = Attack(move)
        fighter.guard = fighter.dash = 0
        fighter.last_move = move.name

    def boundaries(self):
        a, b = self.fighters
        for fighter in self.fighters:
            fighter.x = max(4, min(55, fighter.x))
        if abs(a.x - b.x) < 3.5:
            direction = 1 if a.x <= b.x else -1
            midpoint = max(5.75, min(53.25, (a.x + b.x) / 2))
            a.x, b.x = midpoint - direction * 1.75, midpoint + direction * 1.75
        a.facing = 1 if b.x >= a.x else -1
        b.facing = -a.facing

    def connect(self, side, move, projectile=False):
        attacker, defender = self.fighters[side], self.fighters[1 - side]
        if defender.down > 0 or defender.invincible > 0:
            return False
        if not projectile and (abs(attacker.x - defender.x) > move.reach
                               or abs(attacker.y - defender.y) > 4.5):
            return False
        if move.height == 'grab':
            if defender.y > 0 or defender.vy > 0 or defender.crouch > 0 or defender.stun > 0 or attacker.y > 0:
                return False
            self.throw = Throw(side, move, cpu_break=self.cpu_enabled and side == 0 and self.rng.random() < 0.35)
            for fighter in self.fighters:
                fighter.attack = None
                fighter.queue.clear()
                fighter.stun = 0.4
            self.say('CPU GRAB! G TO BREAK!' if side == 1 else 'GRAB!')
            return True
        if move.height == 'high' and defender.crouch > 0 and defender.y == 0:
            return False
        if move.height == 'low' and defender.y > 0.8:
            return False
        guarded = defender.guard > 0 and defender.attack is None and defender.y == 0
        matching_guard = (move.height == 'low') == (defender.crouch > 0)
        if guarded and matching_guard and not move.breaker:
            defender.stun = 0.12
            defender.hp = max(0, defender.hp - (2 if move.cost else 0))
            attacker.meter = min(100, attacker.meter + 3)
            defender.meter = min(100, defender.meter + 2)
            self.say('BLOCK!')
            return False
        chained = attacker.combo_timer > 0 and (defender.stun > 0 or defender.y > 0)
        if not chained:
            attacker.combo_hits = attacker.combo_damage = 0
        scale = max(0.45, 1 - 0.12 * attacker.combo_hits)
        armor = (defender.attack is not None and defender.attack.move.armor
                 and defender.attack.elapsed <= defender.attack.move.last_hit
                 and move.height != 'low' and not move.launch)
        damage = max(1, round(move.damage * attacker.profile.power * scale * (0.6 if armor else 1)))
        defender.hp = max(0, defender.hp - damage)
        attacker.combo_hits += 1
        attacker.combo_damage += damage
        attacker.combo_timer = 1.1
        attacker.meter = min(100, attacker.meter + 7)
        defender.meter = min(100, defender.meter + 4)
        if not armor:
            defender.attack = None
            defender.queue.clear()
            defender.guard = defender.dash = 0
            defender.stun = max(0.16, move.stun * (0.93 ** (attacker.combo_hits - 1)))
            defender.x += attacker.facing * move.push
            if move.launch:
                defender.vy = move.launch
            final_strike = attacker.attack is None or attacker.attack.resolved >= move.hits
            if (move.down and final_strike) or attacker.combo_hits >= 6:
                defender.down = 0.75
                defender.vy = min(defender.vy, 0)
        self.say(f'{attacker.profile.name}: {move.name}' + (' [ARMOR]' if armor else ''))
        return True

    def cpu_action(self):
        cpu, player = self.fighters[1], self.fighters[0]
        if not cpu.free:
            return
        distance = abs(cpu.x - player.x)
        toward = 'a' if cpu.x > player.x else 'd'
        if distance > 8:
            if cpu.meter >= 35 and self.rng.random() < 0.20:
                self.press(1, 'x')
            else:
                self.press(1, toward)
                if self.rng.random() < 0.35:
                    self.press(1, 'e')
            return
        if player.attack and self.rng.random() < 0.25:
            if player.attack.move.height == 'low':
                self.press(1, 's')
            self.press(1, 'guard')
            return
        choices = ['j', 'j', 'k', 'l', 'u', 'o', 'guard', 's', toward]
        choices += [key for key, move in cpu.profile.skills.items() if cpu.meter >= move.cost]
        action = self.rng.choice(choices)
        self.press(1, action)
        if action == 'j' and self.rng.random() < 0.40:
            self.press(1, 'j')
            self.press(1, 'k')
        elif action == 's':
            self.press(1, 'l')

    def end_round(self):
        health = [fighter.hp / fighter.profile.hp for fighter in self.fighters]
        if health[0] == health[1]:
            self.message = 'DRAW ROUND'
        else:
            winner = 0 if health[0] > health[1] else 1
            self.wins[winner] += 1
            self.message = 'ROUND WIN!' if winner == 0 else 'CPU WINS ROUND'
        self.throw = None
        self.projectiles.clear()
        if max(self.wins) >= 2:
            self.over = True
            self.phase = 'done'
            self.result = f'{"YOU WIN!" if self.wins[0] == 2 else "CPU WINS"} {self.wins[0]}-{self.wins[1]}'
        else:
            self.phase = 'between'
            self.between = 1.7

    def update(self, dt):
        if self.over or self.phase == 'select':
            return
        steps = max(1, math.ceil(dt / 0.02))
        for _ in range(steps):
            if self.over:
                break
            self.tick(dt / steps)

    def tick(self, dt):
        if self.phase == 'between':
            self.between -= dt
            if self.between <= 0:
                self.round += 1
                self.new_round()
                self.phase = 'fight'
            return
        self.elapsed += dt
        self.remaining = max(0, self.remaining - dt)
        self.message_timer = max(0, self.message_timer - dt)
        for fighter in self.fighters:
            was_down = fighter.down > 0
            for field_name in ('stun', 'down', 'guard', 'crouch', 'dash', 'invincible', 'combo_timer'):
                setattr(fighter, field_name, max(0, getattr(fighter, field_name) - dt))
            if was_down and fighter.down == 0:
                fighter.invincible = 0.25
            if fighter.y > 0 or fighter.vy > 0:
                fighter.vy -= 28 * dt
                fighter.y = max(0, fighter.y + fighter.vy * dt)
                if fighter.y == 0:
                    fighter.vy = 0
            if fighter.dash > 0 and fighter.free:
                fighter.x += fighter.facing * 28 * fighter.profile.speed * dt
        self.boundaries()
        if self.throw is not None:
            throw = self.throw
            throw.remaining -= dt
            throw.elapsed += dt
            if throw.cpu_break and throw.elapsed >= 0.16:
                self.press(1, 'g')
            elif throw.remaining <= 0:
                attacker, target = self.fighters[throw.owner], self.fighters[1 - throw.owner]
                damage = round(throw.move.damage * attacker.profile.power)
                target.hp = max(0, target.hp - damage)
                target.down = 0.8
                target.stun = 0
                target.x += attacker.facing * 3
                attacker.stun = 0.25
                attacker.meter = min(100, attacker.meter + 10)
                self.throw = None
                self.say(throw.move.name + '!')
        else:
            if self.cpu_enabled:
                self.cpu_clock -= dt
                if self.cpu_clock <= 0:
                    self.cpu_action()
                    self.cpu_clock = self.rng.uniform(0.18, 0.36)
            for side, fighter in enumerate(self.fighters):
                self.process_queue(side)
                attack = fighter.attack
                if attack is None:
                    continue
                attack.elapsed += dt
                if attack.elapsed <= attack.move.startup:
                    fighter.x += fighter.facing * attack.move.advance * dt
                    self.boundaries()
                while attack.resolved < attack.move.hits and attack.elapsed >= attack.move.startup + attack.resolved * 0.12:
                    attack.resolved += 1
                    if attack.move.projectile:
                        height = 0.5 if attack.move.height == 'low' else fighter.y + 2
                        self.projectiles.append(Projectile(side, fighter.x + fighter.facing * 2, height,
                                                           fighter.facing * attack.move.projectile, attack.move))
                    else:
                        attack.confirmed = self.connect(side, attack.move) or attack.confirmed
                    if self.throw is not None:
                        break
                if self.throw is not None:
                    break
                if attack.elapsed >= attack.move.duration:
                    fighter.attack = None
            remaining = []
            for shot in self.projectiles:
                previous = shot.x
                shot.x += shot.vx * dt
                target = self.fighters[1 - shot.owner]
                crosses = min(previous, shot.x) - 2 <= target.x <= max(previous, shot.x) + 2
                if crosses and target.y - 0.5 <= shot.y <= target.y + 4.5:
                    self.connect(shot.owner, shot.move, projectile=True)
                elif 0 <= shot.x <= 60:
                    remaining.append(shot)
            self.projectiles = remaining
        self.boundaries()
        if self.remaining <= 0 or any(fighter.hp <= 0 for fighter in self.fighters):
            self.end_round()
