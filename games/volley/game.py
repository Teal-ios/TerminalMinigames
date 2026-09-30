"""A small Pikachu-inspired terminal volleyball match against the CPU."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import curses

from arcade_screen import run

W, H, NET = 60, 22, 30
STEP = 1 / 120
INPUT_HOLD = 0.18  # Terminals send key repeats, not key-up events.
SPIKE_WINDOW = 0.32
CPU_REACTION = 0.18


class VolleyGame:
    def __init__(self):
        # Player coordinates use height above the ground, unlike screen rows.
        self.players = [[14.0, 0.0, 0.0], [46.0, 0.0, 0.0]]
        self.scores = [0, 0]
        self.over = False
        self.result = ''
        self.smash = 0.0
        self.rally = self.last_rally = self.best_rally = 0
        self.feedback = ''
        self.feedback_timer = 0.0
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
        self.move_velocity = [0.0, 0.0]
        self.move_direction = 0
        self.move_hold = self.jump_buffer = 0.0
        self.aim_x = self.aim_y = 0
        self.aim_hold = self.spike_cooldown = 0.0
        self.cpu_target = 46.0
        self.cpu_reaction = CPU_REACTION
        self.cpu_smash = 0.0
        self.rally = 0
        self.trail = []
        self.trail_clock = 0.0
        self.hit_effect = None
        self.hit_timer = 0.0

    def lying_down(self, side):
        return self.slide_timer[side] > 0 or self.recovery[side] > 0

    def slide(self, side, direction):
        if not self.lying_down(side) and self.players[side][1] == 0 and self.players[side][2] == 0:
            self.slide_timer[side] = 0.34
            self.facing[side] = 1 if direction >= 0 else -1
            self.move_velocity[side] = 0.0
            if side == 0:
                self.move_hold = self.jump_buffer = 0.0
                self.move_direction = 0

    def jump(self, side):
        player = self.players[side]
        if player[1] == 0 and player[2] == 0 and not self.lying_down(side):
            player[2] = 16.0
            if side == 0:
                self.jump_buffer = 0.0

    def handle(self, key):
        if self.over or self.lying_down(0):
            return
        if key in (curses.KEY_LEFT, ord('a'), ord('A')):
            self.facing[0] = self.move_direction = self.aim_x = -1
            self.move_hold = INPUT_HOLD
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
            self.facing[0] = self.move_direction = self.aim_x = 1
            self.move_hold = INPUT_HOLD
        elif key in (curses.KEY_UP, ord('w'), ord('W')):
            if self.players[0][1] > 0:
                self.aim_y = 1
                self.aim_hold = INPUT_HOLD
                self.jump_buffer = 0.14
            self.jump(0)
        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
            self.aim_y = -1
            self.aim_hold = INPUT_HOLD
        elif key == ord(' '):
            if self.players[0][1] > 0 or self.players[0][2] > 0:
                if self.spike_cooldown == 0:
                    self.smash = SPIKE_WINDOW
                    self.spike_cooldown = 0.5
                    self.spike_aim = (self.aim_x, self.aim_y)
                    self.say('SPIKE READY - meet the ball!', 0.32)
            else:
                self.slide(0, self.facing[0])

    def say(self, message, duration=0.8):
        self.feedback, self.feedback_timer = message, duration

    def point(self, side):
        if self.over:
            return
        self.last_rally = self.rally
        self.best_rally = max(self.best_rally, self.rally)
        self.scores[side] += 1
        if self.scores[side] >= 5:
            self.over = True
            self.result = 'YOU WIN!' if side == 0 else 'CPU WINS - TRY AGAIN!'
        else:
            self.serve(side)
        self.say(f'{"YOUR" if side == 0 else "CPU"} POINT!  '
                 f'{self.last_rally} touches', 0.85)

    def update(self, dt):
        # Small simulation steps keep fast spikes from skipping a player or net.
        remaining = max(0.0, dt)
        while remaining > 1e-9 and not self.over:
            step = min(STEP, remaining)
            self._step(step)
            remaining -= step

    def _step(self, dt):
        old_smash = self.smash
        self.smash = max(0, self.smash - dt)
        if old_smash > 0 and self.smash == 0:
            self.say('MISSED SPIKE - press SPACE just before contact', 0.6)
        self.spike_cooldown = max(0, self.spike_cooldown - dt)
        self.cpu_smash = max(0, self.cpu_smash - dt)
        self.feedback_timer = max(0, self.feedback_timer - dt)
        self.hit_timer = max(0, self.hit_timer - dt)
        self.bounce_cooldown = [max(0, value - dt) for value in self.bounce_cooldown]
        self._think_cpu(dt)
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
                if not self.lying_down(side):
                    if side == 0:
                        target_speed = self.move_direction * 14 if self.move_hold > 0 else 0
                    else:
                        delta = self.cpu_target - self.players[side][0]
                        target_speed = max(-11, min(11, delta * 5))
                    acceleration = 100 if side == 0 else 60
                    velocity = self.move_velocity[side]
                    velocity += max(-acceleration * dt,
                                    min(acceleration * dt, target_speed - velocity))
                    self.move_velocity[side] = velocity
                    low, high = (4, NET - 4) if side == 0 else (NET + 4, W - 4)
                    x = self.players[side][0] + velocity * dt
                    self.players[side][0] = max(low, min(high, x))
                    if not low < x < high:
                        self.move_velocity[side] = 0.0
        self.move_hold = max(0, self.move_hold - dt)
        self.aim_hold = max(0, self.aim_hold - dt)
        if self.move_hold == 0:
            self.aim_x = 0
        if self.aim_hold == 0:
            self.aim_y = 0
        for side, player in enumerate(self.players):
            if player[1] > 0 or player[2] > 0:
                player[2] -= 28 * dt
                player[1] += player[2] * dt
                if player[1] <= 0:
                    player[1] = player[2] = 0.0
                    if side == 0 and self.jump_buffer > 0:
                        self.jump(0)
        self.jump_buffer = max(0, self.jump_buffer - dt)
        if self.serving > 0:
            self.serving = max(0, self.serving - dt)
            return

        self.trail_clock += dt
        if self.trail_clock >= 0.04:
            self.trail_clock -= 0.04
            self.trail.append(tuple(self.ball[:2]))
            self.trail = self.trail[-5:]
        bx, by, vx, vy = self._world_step(self.ball, dt)
        for side, (px, py, player_vy) in enumerate(self.players):
            if self.bounce_cooldown[side] > 0:
                continue
            if (side == 0 and bx >= NET) or (side == 1 and bx <= NET):
                continue
            # Ear tips remain decorative; low diving pose has a wider reach.
            low_pose = self.lying_down(side)
            head = 1.3 if low_pose else py + 4
            reach = 5.2 if low_pose else 3.8
            if abs(bx - px) <= reach and head - 1 <= by <= head + 1.3 and vy < player_vy:
                direction = 1 if side == 0 else -1
                by = head + 1.4
                vx, vy = direction * 10 + (bx - px) * 1.4, 15.0
                message = 'DIVING SAVE!' if low_pose else 'NICE RECEIVE'
                if side == 0 and self.smash > 0 and py > 0:
                    aim_x, aim_y = self.spike_aim
                    perfect = self.smash >= SPIKE_WINDOW - 0.12
                    vx = {-1: 15.0, 0: 21.0, 1: 26.0}[aim_x]
                    if not perfect:
                        vx *= 0.82
                    vy = 15.0 if aim_y > 0 else -8.0 if aim_y < 0 else -2.0
                    if by < 8.5 and aim_y == 0:
                        vy, message = 14.0, 'LOW SET - jump higher to spike'
                    else:
                        message = 'PERFECT SPIKE!' if perfect else 'SPIKE!'
                    self.smash = 0.0
                elif side == 1 and self.cpu_smash > 0 and py > 1 and by > 9:
                    vx, vy = -18.0, -1.0
                    self.cpu_smash = 0.0
                    message = 'CPU SPIKE!'
                self.rally += 1
                self.best_rally = max(self.best_rally, self.rally)
                self.say(message)
                self.hit_effect, self.hit_timer = (bx, by), 0.14
                self.bounce_cooldown[side] = 0.25
        self.ball = [bx, by, vx, vy]
        if by <= 0.6:
            self.point(1 if bx < NET else 0)

    @staticmethod
    def _world_step(ball, dt):
        """Shared court physics for the real ball and CPU's bounded prediction."""
        bx, by, vx, vy = ball
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

        # Resolve the top first so a descending ball is not reflected sideways.
        if abs(bx - NET) <= 0.7 and old_y > 7.5 >= by:
            by, vy = 7.6, abs(vy) * 0.85
        elif by <= 7.5:
            if old_x < NET and bx >= NET - 0.6:
                bx, vx = NET - 0.7, -abs(vx)
            elif old_x > NET and bx <= NET + 0.6:
                bx, vx = NET + 0.7, abs(vx)
        return [bx, by, vx, vy]

    def predict_landing(self):
        projected = self.ball[:]
        for _ in range(600):
            projected = self._world_step(projected, 1 / 60)
            if projected[1] <= 0.6:
                break
        return projected[0]

    def _think_cpu(self, dt):
        if self.serving > 0:
            return
        self.cpu_reaction -= dt
        if self.cpu_reaction > 0:
            return
        self.cpu_reaction += CPU_REACTION
        landing = self.predict_landing()
        self.cpu_target = max(NET + 4, min(W - 4, landing)) if landing > NET else 44.0
        if self.lying_down(1):
            return
        px, py, _ = self.players[1]
        bx, by, vx, vy = self.ball
        if bx <= NET or vy >= 0:
            return
        distance = abs(bx - px)
        if py == 0:
            if by < 4 and 3.8 < distance < 9:
                self.slide(1, 1 if bx > px else -1)
            elif distance < 3 and 5 < by < 11:
                self.jump(1)
        elif distance < 4 and py + 3 < by < py + 7:
            self.cpu_smash = 0.25

    def draw(self, screen):
        screen.centered(0, 'P I K A   V O L L E Y', 2)
        screen.centered(1, f'RALLY {self.rally:02d}   BEST {self.best_rally:02d}', 7)
        screen.centered(2, f'YOU  {self.scores[0]}   :   {self.scores[1]}  CPU     FIRST TO 5', 1)
        screen.border(3, H + 2)

        def court(x, y, text, color=0):
            screen.text(4 + H - 1 - int(y), 2 + int(x), text, color)

        for x in range(1, W, 2):
            court(x, 0, '.', 7)
        court(self.ball[0], 0, '_', 1)
        for x, y in self.trail:
            if 0 < y < H:
                court(x, y, '.', 7)
        for y in range(7):
            court(NET, y, '|', 1)
        court(NET, 7, '+', 1)
        for side, (x, y, _) in enumerate(self.players):
            self.draw_pikachu(court, side, x, y)
        if self.hit_timer > 0:
            x, y = self.hit_effect
            court(max(1, min(W - 2, x + 1)), min(H - 1, y), '*', 2)
        court(self.ball[0], self.ball[1], 'O', 3)
        if self.serving > 0 and not self.over:
            label = 'YOUR SERVE' if self.server == 0 else 'CPU SERVE'
            beat = 'READY' if self.serving > 0.4 else 'GO!'
            screen.centered(6, f'{label} - {beat}', 2)
        screen.text(28, 1, 'ARROWS/WASD: Move/Jump   SPACE: Ground slide / Air spike')
        screen.text(29, 1, 'Air aim: UP lob / DOWN drop / LEFT short / RIGHT deep')
        status = 'SLIDING!' if self.slide_timer[0] > 0 else 'GETTING UP...' if self.recovery[0] > 0 else ''
        screen.centered(30, status or (self.feedback if self.feedback_timer > 0 else
                        'Time SPACE just before contact for a PERFECT spike'), 2)
        screen.text(31, 1, 'P: Pause  R: Restart  Q: Quit    Tap/repeat to move')

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
