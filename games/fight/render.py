"""Sub-cell vector stick animation using Unicode Braille (2 x 4 dots/cell)."""
import math

from .combat import hitbox


class Surface:
    BITS = ((1, 8), (2, 16), (4, 32), (64, 128))

    def __init__(self, width=62, height=16):
        self.width, self.height = width, height
        self.pixels = {}
        self.order = 0

    def dot(self, x, y, color=8):
        x, y = round(x), round(y)
        if 0 <= x < self.width * 2 and 0 <= y < self.height * 4:
            self.order += 1
            self.pixels[x, y] = (color, self.order)

    def disc(self, x, y, radius, color=8):
        for py in range(math.floor(y - radius), math.ceil(y + radius) + 1):
            for px in range(math.floor(x - radius), math.ceil(x + radius) + 1):
                if (px - x) ** 2 + (py - y) ** 2 <= radius * radius:
                    self.dot(px, py, color)

    def line(self, x1, y1, x2, y2, color=8, thick=0.65):
        steps = max(1, math.ceil(max(abs(x2 - x1), abs(y2 - y1)) * 1.7))
        for step in range(steps + 1):
            t = step / steps
            self.disc(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, thick, color)

    def path(self, points, color=8, thick=0.65):
        for start, end in zip(points, points[1:]):
            self.line(*start, *end, color, thick)

    def ring(self, x, y, radius, color=8, start=0, end=math.tau):
        steps = max(10, math.ceil(abs(end - start) * radius * 1.5))
        points = [(x + math.cos(start + (end - start) * i / steps) * radius,
                   y + math.sin(start + (end - start) * i / steps) * radius)
                  for i in range(steps + 1)]
        self.path(points, color)

    def flush(self, screen, top=9, left=1):
        cells = {}
        for (x, y), (color, order) in self.pixels.items():
            key = (x // 2, y // 4)
            mask, old_color, old_order = cells.get(key, (0, color, -1))
            cells[key] = (mask | self.BITS[y % 4][x % 2], color if order > old_order else old_color,
                          max(order, old_order))
        for (x, y), (mask, color, _) in cells.items():
            screen.text(top + y, left + x, chr(0x2800 + mask), color)


def limb_pose(fighter, clock):
    """Animated joints in local pixels: up is positive; facing mirrors x."""
    bob = math.sin(clock * 4) * 0.6
    p = {'hip': (0, 13 + bob), 'shoulder': (0, 22 + bob), 'head': (0, 27 + bob),
         'elbow': (4, 18 + bob), 'hand': (6, 21 + bob),
         'back_elbow': (-4, 18), 'back_hand': (-3, 13),
         'knee': (3, 7), 'foot': (6, 0), 'back_knee': (-4, 6), 'back_foot': (-6, 0)}
    if fighter.down > 0:
        return {'hip': (-2, 2), 'shoulder': (5, 3), 'head': (10, 3),
                'elbow': (4, 0), 'hand': (0, 0), 'back_elbow': (5, 5), 'back_hand': (9, 0),
                'knee': (-6, 4), 'foot': (-11, 0), 'back_knee': (-5, 1), 'back_foot': (-10, 0)}
    if fighter.crouch > 0 and fighter.y == 0:
        p.update(hip=(-2, 4), shoulder=(0, 9), head=(1, 13), elbow=(4, 8), hand=(5, 11),
                 back_elbow=(-5, 5), back_hand=(-4, 1), knee=(4, 4), back_knee=(-5, 2))
    if fighter.move_timer > 0:
        gait = math.sin(clock * 18)
        p.update(knee=(4 + gait * 2, 7), foot=(6 * gait, max(0, gait * 3)),
                 back_knee=(-4 - gait * 2, 7), back_foot=(-6 * gait, max(0, -gait * 3)))
    if fighter.y > 0:
        p.update(knee=(5, 10), foot=(8, 7), back_knee=(-6, 9), back_foot=(-3, 4))
    if fighter.dash > 0:
        p.update(hip=(-1, 11), shoulder=(5, 19), head=(8, 23), hand=(12, 16),
                 elbow=(9, 15), foot=(-7, 0), back_foot=(-11, 4))
    if fighter.guard > 0:
        shoulder = p['shoulder']
        p.update(elbow=(5, shoulder[1] - 3), hand=(6, shoulder[1] + 5),
                 back_elbow=(1, shoulder[1] - 5), back_hand=(5, shoulder[1] + 3))
    if fighter.stun > 0:
        p.update(shoulder=(-4, 21), head=(-7, 26), elbow=(1, 16), hand=(5, 14),
                 back_elbow=(-8, 17), back_hand=(-11, 22))
    attack = fighter.attack
    if attack:
        move, t = attack.move, attack.elapsed
        if t < move.startup:
            wind = math.sin(t / max(0.01, move.startup) * math.pi / 2)
            p.update(shoulder=(-2 * wind, 22), head=(-2 * wind, 27),
                     elbow=(-5 * wind, 18), hand=(-3 * wind, 23))
        else:
            recover = max(0, t - move.last_hit - move.active) / max(0.01, move.recovery)
            extension = max(0, 1 - recover)
            reach = (move.reach - 1.2) * 2
            reach = min(reach, 13) if move.projectile else reach
            # Keep the striking limb at its collision reach during active frames.
            reach *= extension
            if move.height == 'low':
                p.update(hip=(-2, 5), shoulder=(-3, 12), head=(-3, 17), knee=(reach / 2, 3), foot=(reach, 2))
            elif move.launch:
                p.update(shoulder=(2, 23), head=(1, 28), elbow=(reach / 2, 26), hand=(reach, 32))
            elif 'KICK' in move.name or 'AXE' in move.name:
                p.update(hip=(-2, 14), shoulder=(-4, 23), head=(-5, 28),
                         knee=(reach / 2, 15), foot=(reach, 14), back_foot=(-5, 0))
            else:
                y = 21 if move.height == 'high' else 15
                p.update(shoulder=(2 * extension, 22), head=(1, 27),
                         elbow=(reach * 0.5, y + 1), hand=(reach, y))
    return p


def figure(surface, fighter, clock, shift=0, floor=60, grapple=None):
    p = limb_pose(fighter, clock)
    if grapple == 'owner':
        p.update(shoulder=(2, 20), head=(3, 25), elbow=(6, 18), hand=(9, 21),
                 back_elbow=(5, 15), back_hand=(9, 18))
    elif grapple == 'victim':
        p.update(shoulder=(3, 19), head=(6, 23), elbow=(7, 14), hand=(8, 18),
                 back_elbow=(-1, 14), back_hand=(4, 17))
    base_x, base_y = fighter.x * 2 + 2 + shift, floor - fighter.y * 4
    facing = fighter.facing
    color = 8 if fighter.flash > 0 else fighter.profile.color
    body = 8
    heavy = fighter.profile.name == 'IRON'
    thick = 1.1 if heavy else 0.8

    def point(node):
        x, y = p[node] if isinstance(node, str) else node
        return base_x + facing * x, base_y - y

    def limb(*nodes, tint=body, weight=thick):
        surface.path([point(node) for node in nodes], tint, weight)

    # Back limbs are dimmer, keeping crossed limbs readable at small sizes.
    limb('hip', 'back_knee', 'back_foot', tint=7)
    limb('shoulder', 'back_elbow', 'back_hand', tint=color)
    limb('hip', 'shoulder', weight=1.5 if heavy else 1.1)
    limb('hip', 'knee', 'foot')
    limb('shoulder', 'elbow', 'hand')
    head_x, head_y = point('head')
    surface.disc(head_x, head_y, 3.2 if heavy else 2.7, 8)
    if fighter.profile.name == 'STRIKER':
        hx, hy = p['head']
        hair = [(hx - 3, hy + 1), (hx - 4, hy + 5), (hx - 1, hy + 3),
                (hx, hy + 6), (hx + 1, hy + 3), (hx + 3, hy + 5), (hx + 3, hy + 1)]
        surface.path([point(v) for v in hair], 3, 0.85)
        limb((hx - 3, hy), (hx + 2, hy), tint=3)
        flutter = math.sin(clock * 10)
        limb((hx - 3, hy), (hx - 7, hy + flutter), (hx - 10, hy - 1), tint=3)
        surface.disc(*point('hand'), 1.6, color)
    elif fighter.profile.name == 'RUSH':
        hx, hy = p['head']
        surface.ring(head_x, head_y, 3, 6, math.pi, math.tau)
        limb((hx - 2, hy + 1), (hx - 6, hy + 4), (hx - 9, hy + 2 + math.sin(clock * 8)), tint=6, weight=1)
        sx, sy = p['shoulder']
        limb((sx + 2, sy + 2), (sx - 4, sy + 1), (sx - 9, sy + 3),
             (sx - 13, sy + math.sin(clock * 10) * 2), tint=6, weight=1)
    else:
        hx, hy = p['head']
        for offset in (-1, 0, 1):
            limb((hx + offset, hy + 2), (hx + offset, hy + 6), tint=2, weight=0.8)
        limb('elbow', 'hand', tint=2, weight=2)
        surface.disc(*point('hand'), 2, 2)
        surface.disc(*point('back_hand'), 1.7, 2)
    # A cut-out eye turns a circle into a face pointing at the opponent.
    ex, ey = round(head_x + facing * 1.5), round(head_y - 0.5)
    surface.pixels.pop((ex, ey), None)
    if fighter.attack:
        move, t = fighter.attack.move, fighter.attack.elapsed
        if move.startup <= t <= move.last_hit + move.active:
            hand = 'foot' if move.height == 'low' or 'KICK' in move.name or 'AXE' in move.name else 'hand'
            tipx, tipy = point(hand)
            shoulder = point('hip' if hand == 'foot' else 'shoulder')
            surface.line(shoulder[0], shoulder[1] + 3, tipx - facing, tipy + 2, color)
            surface.ring(tipx, tipy, 2.4, color, -1.4, 1.4)
        elif t < move.startup and move.cost:
            surface.ring(*point('hand'), 2 + math.sin(clock * 24) * 0.6, color)


def draw_arena(screen, game, guide=False):
    s = Surface()
    shift = math.sin(game.visual_time * 90) * 1.5 if game.shake > 0 else 0
    # Quiet rooftop backdrop, well below the characters' contrast.
    for x, roof in ((4, 25), (23, 18), (43, 28), (73, 24), (95, 15), (115, 22)):
        s.path([(x, 51), (x, roof), (x + 12, roof), (x + 12, 51)], 7)
        for row in range(roof + 4, 49, 6):
            for col in (x + 3, x + 8):
                s.line(col, row, col + 1, row, 7)
    s.ring(60, 8, 5, 7)
    s.line(0, 61, 123, 61, 1)
    for x in range(0, 125, 12):
        s.line(x, 63, x + 5, 63, 7)
    for effect in game.effects:
        if effect.kind == 'trail':
            x, y = effect.x * 2 + 2 + shift, 60 - effect.y * 4
            s.ring(x, y - 27, 2.5, 7)
            s.path([(x, y - 24), (x, y - 12), (x - 5, y), (x, y - 12), (x + 5, y)], 7)
    for side, fighter in enumerate(game.fighters):
        grapple = ('owner' if side == game.throw.owner else 'victim') if game.throw else None
        figure(s, fighter, game.elapsed, shift, grapple=grapple)
    for shot in game.projectiles:
        x, y = shot.x * 2 + 2 + shift, 60 - shot.y * 4
        tint = game.fighters[shot.owner].profile.color
        direction = 1 if shot.vx > 0 else -1
        for offset in (-2, 0, 2):
            s.line(x - direction * 9, y + offset, x, y + offset / 2, tint)
        s.disc(x, y, 2, 8)
        s.ring(x, y, 3.4, tint)
    for effect in game.effects:
        x, y = effect.x * 2 + 2 + shift, 60 - effect.y * 4
        progress = effect.age / effect.ttl
        radius = 2 + progress * 10
        if effect.kind in ('hit', 'counter'):
            for ray in range(9):
                angle = ray * math.tau / 9 + 0.3
                length = radius * (1.4 if ray % 2 == 0 else 0.8)
                s.line(x + math.cos(angle) * radius * .3, y + math.sin(angle) * radius * .3,
                       x + math.cos(angle) * length, y + math.sin(angle) * length, effect.color)
            if progress < 0.6:
                s.disc(x, y, max(0.8, 3 * (1 - progress)), 8)
        elif effect.kind in ('block', 'grab'):
            s.ring(x, y, 3 + progress * 5, effect.color)
        elif effect.kind in ('dust', 'slam'):
            width = (8 if effect.kind == 'slam' else 4) * progress + 2
            s.path([(x - width, y - 1), (x - width / 2, y - 3), (x, y - 1),
                    (x + width / 2, y - 3), (x + width, y - 1)], effect.color)
            if effect.kind == 'slam':
                s.line(x - width * 2, y - 0.5, x + width * 2, y - 0.5, effect.color)
        elif effect.kind == 'launch':
            for dx in (-3, 0, 3):
                s.line(x + dx, y - progress * 14, x + dx, y - progress * 14 - 6, effect.color)
        elif effect.kind == 'super':
            s.ring(x, y, 8 + progress * 26, effect.color)
            for ray in range(8):
                a = ray * math.tau / 8 + progress
                s.line(x + math.cos(a) * 9, y + math.sin(a) * 9,
                       x + math.cos(a) * 30, y + math.sin(a) * 30, effect.color)
    if guide:
        for fighter in game.fighters:
            if fighter.attack and not fighter.attack.move.projectile:
                x1, y1, x2, y2 = hitbox(fighter, fighter.attack.move)
                s.path([(x1 * 2 + 2, 60 - y1 * 4), (x2 * 2 + 2, 60 - y1 * 4),
                        (x2 * 2 + 2, 60 - y2 * 4), (x1 * 2 + 2, 60 - y2 * 4),
                        (x1 * 2 + 2, 60 - y1 * 4)], fighter.profile.color)
    s.flush(screen)
    for effect in game.effects:
        if effect.kind == 'damage':
            row = max(9, min(23, round(24 - effect.y - effect.age * 3)))
            col = max(1, min(61 - len(effect.text), round(effect.x)))
            screen.text(row, col, effect.text, effect.color)
