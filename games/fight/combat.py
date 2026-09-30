"""Deterministic combat rules, buffered strings, throws, meter, and CPU."""
from collections import deque
from dataclasses import dataclass, field, replace
import math
import random

from .moves import AIR_KICK, BASIC, CHAINS, ROSTER, SWEEP, Move, Profile


@dataclass
class Attack:
    move: Move
    elapsed: float = 0.0
    resolved: int = 0
    confirmed: bool = False
    confirmed_at: float = 0


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
    guard_dir: int = 0
    blockstun: float = 0
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
    move_dir: int = 0
    move_timer: float = 0
    vx: float = 0
    knockback: float = 0
    flash: float = 0

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


@dataclass
class Effect:
    kind: str
    x: float
    y: float
    ttl: float
    color: int = 2
    text: str = ''
    age: float = 0


def hitbox(fighter, move):
    """World-space reach shared by collision, limb extension and range guide."""
    a = fighter.x + fighter.facing * 0.7
    b = fighter.x + fighter.facing * max(1, move.reach - 1.2)
    low, high = (4.5, 6.2) if move.height == 'high' else (2, 4.8)
    if move.height == 'low':
        low, high = 0, 1.3
    elif move.launch:
        low, high = 1.5, 8.0
    elif move.height == 'grab':
        low, high = 0, 6
    return min(a, b), fighter.y + low, max(a, b), fighter.y + high


def hurtbox(fighter):
    height = 3.3 if fighter.crouch > 0 and fighter.y == 0 else 6.2
    return fighter.x - 1.2, fighter.y, fighter.x + 1.2, fighter.y + height


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
        self.effects = []
        self.hitstop = self.shake = 0.0
        self.visual_time = 0.0
        self.trail_clock = 0.0
        self.health_trail = [float(f.hp) for f in self.fighters]

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

    def effect(self, kind, x, y, ttl=0.3, color=2, text=''):
        self.effects.append(Effect(kind, x, y, ttl, color, text))
        self.effects = self.effects[-80:]

    def press(self, side, action):
        if self.phase != 'fight' or self.over:
            return
        fighter = self.fighters[side]
        if self.throw is not None:
            if action == 'g' and side != self.throw.owner:
                self.effect('block', fighter.x, 3, color=1)
                self.throw = None
                for person in self.fighters:
                    person.stun = 0.18
                self.say('THROW BREAK!')
            return
        if not fighter.free and fighter.blockstun <= 0:
            return
        if action in BASIC or action in fighter.profile.skills:
            if len(fighter.queue) < 3:
                fighter.queue.append((action, self.elapsed))
            self.process_queue(side)
            return
        if action in ('a', 'd'):
            fighter.move_dir = -1 if action == 'a' else 1
            fighter.move_timer = 0.26
            opponent = self.fighters[1 - side]
            away = (opponent.x - fighter.x) * fighter.move_dir < 0
            fighter.guard = 0.32 if away and fighter.y == 0 and fighter.vy <= 0 else 0
            fighter.guard_dir = fighter.move_dir if fighter.guard else 0
            if fighter.guard:
                fighter.dash = 0
            return
        if fighter.attack is not None:
            return
        if action == 'guard' and fighter.y == 0 and fighter.vy <= 0:
            fighter.guard, fighter.guard_dir = 0.7, 0
            fighter.move_timer = fighter.vx = fighter.dash = 0
            return
        if not fighter.free:
            return
        if action == 'w' and fighter.y == 0:
            fighter.vy = 16
            fighter.crouch = fighter.guard = 0
            self.effect('dust', fighter.x, 0, color=7)
        elif action == 's' and fighter.y == 0:
            fighter.crouch = 0.6
        elif action == 'e' and fighter.y == 0:
            fighter.dash = 0.18
            fighter.guard = 0
            self.effect('dust', fighter.x, 0, color=fighter.profile.color)

    def process_queue(self, side):
        fighter = self.fighters[side]
        while fighter.queue and self.elapsed - fighter.queue[0][1] > 0.75:
            fighter.queue.popleft()
        if not fighter.free or not fighter.queue or self.throw is not None or self.hitstop > 0:
            return
        attack = fighter.attack
        if attack is not None and not (attack.confirmed and attack.resolved >= attack.move.hits
                                       and attack.elapsed >= attack.confirmed_at + 0.045):
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
        if action not in fighter.profile.skills:
            move = replace(move, reach=move.reach * fighter.profile.reach_scale)
        if move.cost > fighter.meter:
            if side == 0:
                self.say(f'NEED {move.cost} METER FOR {move.name}')
            return
        fighter.meter -= move.cost
        fighter.history.append((action, self.elapsed))
        fighter.attack = Attack(move)
        fighter.guard = fighter.dash = 0
        fighter.move_timer = fighter.vx = 0
        fighter.last_move = move.name
        if move.cost == 100:
            self.effect('super', fighter.x, 3, 0.55, fighter.profile.color, move.name)
            self.hitstop = 0.12
            self.say('SUPER! ' + move.name)

    def boundaries(self):
        a, b = self.fighters
        for fighter in self.fighters:
            fighter.x = max(4, min(55, fighter.x))
        if abs(a.x - b.x) < 3.5:
            direction = 1 if a.x <= b.x else -1
            midpoint = max(5.75, min(53.25, (a.x + b.x) / 2))
            a.x, b.x = midpoint - direction * 1.75, midpoint + direction * 1.75
        if a.attack is None:
            a.facing = 1 if b.x >= a.x else -1
        if b.attack is None:
            b.facing = 1 if a.x >= b.x else -1
        for fighter, opponent in ((a, b), (b, a)):
            if fighter.guard_dir and (opponent.x - fighter.x) * fighter.guard_dir >= 0:
                fighter.guard = 0

    @staticmethod
    def guarding(fighter):
        return (fighter.guard > 0 and fighter.attack is None and fighter.y == 0
                and fighter.vy <= 0 and fighter.down <= 0
                and (fighter.stun <= 0 or fighter.blockstun > 0))

    def connect(self, side, move, projectile=False):
        attacker, defender = self.fighters[side], self.fighters[1 - side]
        if defender.down > 0 or defender.invincible > 0:
            return 'miss'
        if not projectile:
            ax1, ay1, ax2, ay2 = hitbox(attacker, move)
            bx1, by1, bx2, by2 = hurtbox(defender)
            if ((defender.x - attacker.x) * attacker.facing <= 0
                    or ax2 < bx1 or ax1 > bx2 or ay2 < by1 or ay1 > by2):
                return 'miss'
        if move.height == 'grab':
            if (defender.y > 0 or defender.vy > 0
                    or (defender.crouch > 0 and not self.guarding(defender))
                    or defender.stun > 0 or attacker.y > 0):
                return 'miss'
            self.throw = Throw(side, move, cpu_break=self.cpu_enabled and side == 0 and self.rng.random() < 0.35)
            for fighter in self.fighters:
                fighter.attack = None
                fighter.queue.clear()
                fighter.stun = 0.4
                fighter.guard = fighter.blockstun = fighter.move_timer = fighter.vx = 0
            self.say('CPU GRAB! G TO BREAK!' if side == 1 else 'GRAB!')
            self.effect('grab', (attacker.x + defender.x) / 2, 3, 0.3, 6)
            return 'hit'
        if move.height == 'high' and defender.crouch > 0 and defender.y == 0:
            return 'miss'
        if move.height == 'low' and defender.y > 0.8:
            return 'miss'
        if self.guarding(defender):
            defender.stun = defender.blockstun = 0.12
            defender.guard = max(defender.guard, 0.20)
            defender.vx = 0
            attacker.meter = min(100, attacker.meter + 3)
            defender.meter = min(100, defender.meter + 2)
            self.say('BLOCK!')
            self.hitstop = max(self.hitstop, 0.025)
            self.effect('block', defender.x - attacker.facing, defender.y + 3.5, 0.22, 1)
            return 'block'
        chained = attacker.combo_timer > 0 and (defender.stun > 0 or defender.y > 0)
        if not chained:
            attacker.combo_hits = attacker.combo_damage = 0
        scale = max(0.45, 1 - 0.12 * attacker.combo_hits)
        armor = (defender.attack is not None and defender.attack.move.armor
                 and defender.attack.elapsed <= defender.attack.move.last_hit
                 and move.height != 'low' and not move.launch)
        counter = (not armor and defender.attack is not None
                   and defender.attack.elapsed < defender.attack.move.startup)
        damage = max(1, round(move.damage * attacker.profile.power * scale
                              * (0.6 if armor else 1) * (1.2 if counter else 1)))
        defender.hp = max(0, defender.hp - damage)
        attacker.combo_hits += 1
        attacker.combo_damage += damage
        attacker.combo_timer = 1.1
        attacker.meter = min(100, attacker.meter + 7)
        defender.meter = min(100, defender.meter + 4)
        defender.flash = 0.12
        impact_y = defender.y + (1 if move.height == 'low' else 4)
        self.effect('counter' if counter else 'hit', defender.x - attacker.facing, impact_y, 0.24,
                    3 if counter else attacker.profile.color)
        self.effect('damage', defender.x, defender.y + 7, 0.65, 8, str(damage))
        self.hitstop = max(self.hitstop, 0.07 if counter or move.damage >= 12 else 0.035)
        self.shake = 0.22 if move.damage >= 12 else 0.09
        if not armor:
            defender.attack = None
            defender.queue.clear()
            defender.guard = defender.dash = 0
            defender.blockstun = defender.vx = 0
            defender.stun = max(0.16, move.stun * (0.93 ** (attacker.combo_hits - 1))) + (0.1 if counter else 0)
            defender.knockback = attacker.facing * move.push * 9
            defender.move_timer = 0
            if move.launch:
                defender.vy = move.launch
                self.effect('launch', defender.x, defender.y + 1, 0.38, attacker.profile.color)
            elif defender.y > 0:
                defender.vy = max(3, defender.vy)
            final_strike = attacker.attack is None or attacker.attack.resolved + 1 >= move.hits
            if (move.down and final_strike) or attacker.combo_hits >= 6:
                defender.down = 0.75
                defender.vy = min(defender.vy, 0)
        self.say(('COUNTER! ' if counter else '') + f'{attacker.profile.name}: {move.name}' + (' [ARMOR]' if armor else ''))
        return 'hit'

    def cpu_action(self):
        cpu, player = self.fighters[1], self.fighters[0]
        if not cpu.free:
            return
        distance = abs(cpu.x - player.x)
        toward = 'a' if cpu.x > player.x else 'd'
        if self.guarding(player):
            if distance <= BASIC['o'].reach * cpu.profile.reach_scale:
                self.press(1, 'o')
            else:
                self.press(1, toward)
                if distance > 7:
                    self.press(1, 'e')
            return
        if distance > 8:
            if cpu.meter >= 35 and self.rng.random() < 0.20:
                self.press(1, 'x')
            else:
                self.press(1, toward)
                if self.rng.random() < 0.35:
                    self.press(1, 'e')
            return
        if player.attack and distance <= player.attack.move.reach + 1 and self.rng.random() < 0.25:
            if player.attack.move.height == 'low':
                self.press(1, 's')
            self.press(1, 'guard')
            return
        # Pick reachable attacks instead of repeatedly jabbing into empty space.
        choices = ['guard', toward]
        choices += [key for key, move in BASIC.items()
                    if distance <= move.reach * cpu.profile.reach_scale]
        if distance <= BASIC['j'].reach * cpu.profile.reach_scale:
            choices.append('j')
        if distance <= SWEEP.reach * cpu.profile.reach_scale:
            choices.append('s')
        choices += [key for key, move in cpu.profile.skills.items()
                    if cpu.meter >= move.cost and distance <= move.reach + move.advance * move.startup]
        if player.y > 0 and distance <= BASIC['l'].reach * cpu.profile.reach_scale:
            choices += ['l', 'l']
        action = self.rng.choice(choices)
        self.press(1, action)
        if action == 'j' and self.rng.random() < 0.40:
            self.press(1, 'j')
            self.press(1, 'k')
        elif action == 's':
            self.press(1, 'l')
        elif action == 'l' and self.rng.random() < 0.25:
            self.press(1, 'l')
            self.press(1, 'k')

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
        self.visual_time += dt
        self.shake = max(0, self.shake - dt)
        for effect in self.effects:
            effect.age += dt
        self.effects = [effect for effect in self.effects if effect.age < effect.ttl]
        for index, fighter in enumerate(self.fighters):
            self.health_trail[index] = max(fighter.hp, self.health_trail[index] - dt * 26)
        if self.hitstop > 0:
            self.hitstop = max(0, self.hitstop - dt)
            return
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
            for field_name in ('stun', 'blockstun', 'down', 'guard', 'crouch', 'dash', 'invincible', 'combo_timer', 'move_timer', 'flash'):
                setattr(fighter, field_name, max(0, getattr(fighter, field_name) - dt))
            if was_down and fighter.down == 0:
                fighter.invincible = 0.25
            if fighter.y > 0 or fighter.vy > 0:
                fighter.vy -= 28 * dt
                fighter.y = max(0, fighter.y + fighter.vy * dt)
                if fighter.y == 0:
                    self.effect('slam' if fighter.down > 0 else 'dust', fighter.x, 0, 0.3, fighter.profile.color)
                    fighter.vy = 0
            fighter.x += fighter.knockback * dt
            fighter.knockback *= max(0, 1 - dt * 12)
            target_vx = 0
            if fighter.move_timer > 0 and fighter.free and fighter.attack is None:
                pace = 0.6 if self.guarding(fighter) else 1
                target_vx = fighter.move_dir * 15 * fighter.profile.speed * pace
            if not fighter.free or fighter.attack is not None:
                fighter.vx = 0
            else:
                fighter.vx += max(-150 * dt, min(150 * dt, target_vx - fighter.vx))
                fighter.x += fighter.vx * dt
            if fighter.dash > 0 and fighter.free:
                fighter.x += fighter.facing * 28 * fighter.profile.speed * dt
        self.trail_clock -= dt
        if self.trail_clock <= 0:
            self.trail_clock = 0.06
            for fighter in self.fighters:
                if fighter.dash > 0 or (fighter.attack and fighter.attack.move.advance > 0):
                    self.effect('trail', fighter.x, fighter.y, 0.22, fighter.profile.color)
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
                self.effect('slam', target.x, 0, 0.4, 3)
                self.effect('damage', target.x, 5, 0.65, 8, str(damage))
                self.hitstop, self.shake = 0.09, 0.3
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
                    strike_end = attack.move.startup + attack.resolved * 0.12 + attack.move.active
                    if attack.elapsed > strike_end:
                        attack.resolved += 1
                        continue
                    if attack.move.projectile:
                        height = 0.5 if attack.move.height == 'low' else fighter.y + 2
                        self.projectiles.append(Projectile(side, fighter.x + fighter.facing * 2, height,
                                                           fighter.facing * attack.move.projectile, attack.move))
                        attack.resolved += 1
                    else:
                        result = self.connect(side, attack.move)
                        if result == 'hit':
                            attack.confirmed = True
                            attack.confirmed_at = attack.elapsed
                        if result != 'miss' or attack.elapsed >= strike_end:
                            attack.resolved += 1
                        else:
                            break
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
