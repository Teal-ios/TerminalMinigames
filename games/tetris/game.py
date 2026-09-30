"""Terminal falling-block puzzle with an animated, atomic line-clear phase."""
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import curses
from dataclasses import dataclass, replace
import random

from arcade_screen import run

WIDTH, HEIGHT = 10, 20
CLEAR_TIME, LOCK_TIME = .48, .4
SHAPES = {
    'I': ((0, 1), (1, 1), (2, 1), (3, 1)),
    'O': ((0, 0), (1, 0), (0, 1), (1, 1)),
    'T': ((1, 0), (0, 1), (1, 1), (2, 1)),
    'S': ((1, 0), (2, 0), (0, 1), (1, 1)),
    'Z': ((0, 0), (1, 0), (1, 1), (2, 1)),
    'J': ((0, 0), (0, 1), (1, 1), (2, 1)),
    'L': ((2, 0), (0, 1), (1, 1), (2, 1)),
}
COLORS = {'I': 1, 'O': 2, 'T': 6, 'S': 4, 'Z': 3, 'J': 8, 'L': 2}


@dataclass
class Piece:
    kind: str
    x: int = 3
    y: int = -1
    rotation: int = 0


def offsets(piece):
    points = SHAPES[piece.kind]
    size = 4 if piece.kind == 'I' else 2 if piece.kind == 'O' else 3
    for _ in range(piece.rotation % 4):
        points = tuple((size - 1 - y, x) for x, y in points)
    return points


class TetrisGame:
    start_prompt_row = 26

    def __init__(self, rng=None, best=0):
        self.rng = rng if rng is not None else random.Random()
        self.board = [[None] * WIDTH for _ in range(HEIGHT)]
        self.bag, self.next = [], []
        self.active = self.held = None
        self.hold_used = False
        self.score, self.lines, self.combo, self.best = 0, 0, 0, best
        self.fall_clock = self.lock_clock = 0.0
        self.lock_resets = 0
        self.clear_rows = []
        self.clear_elapsed = self.pending_points = 0
        self.message, self.message_timer = 'BUILD FULL ROWS. LEAVE NO GAPS.', 2.0
        self.over, self.result = False, ''
        self.spawn()

    @property
    def level(self):
        return 1 + self.lines // 10

    @property
    def gravity_interval(self):
        return max(.06, .8 * .83 ** (self.level - 1))

    def restart(self):
        return type(self)(best=max(self.best, self.score))

    def take(self):
        if not self.bag:
            self.bag = list(SHAPES)
            self.rng.shuffle(self.bag)
        return self.bag.pop()

    def spawn(self, kind=None, reset_hold=True):
        while len(self.next) < 4:
            self.next.append(self.take())
        if kind is None:
            kind = self.next.pop(0)
        self.active = Piece(kind, 4 if kind == 'O' else 3)
        self.fall_clock = self.lock_clock = 0.0
        self.lock_resets = 0
        if reset_hold:
            self.hold_used = False
        if not self.valid(self.active):
            self.end_game()

    def end_game(self):
        self.over = True
        self.result = f'TOP OUT! SCORE {self.score}'
        self.best = max(self.best, self.score)

    def cells(self, piece=None, y=None):
        piece = self.active if piece is None else piece
        if piece is None:
            return []
        base_y = piece.y if y is None else y
        return [(piece.x + x, base_y + dy) for x, dy in offsets(piece)]

    def valid(self, piece):
        return all(0 <= x < WIDTH and -4 <= y < HEIGHT
                   and (y < 0 or not self.board[y][x]) for x, y in self.cells(piece))

    def grounded(self):
        return self.active is not None and not self.valid(replace(self.active, y=self.active.y + 1))

    def ghost_y(self):
        y = self.active.y
        while self.valid(replace(self.active, y=y + 1)):
            y += 1
        return y

    def manipulate(self, candidate):
        if not self.valid(candidate):
            return False
        was_grounded = self.grounded()
        self.active = candidate
        if was_grounded and self.lock_resets < 12:
            self.lock_clock = 0
            self.lock_resets += 1
        return True

    def rotate(self, direction):
        if self.active.kind == 'O':
            return
        turned = replace(self.active, rotation=(self.active.rotation + direction) % 4)
        # A small, deterministic wall/floor kick system, not full guideline SRS.
        for dx, dy in ((0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1), (0, -2)):
            if self.manipulate(replace(turned, x=turned.x + dx, y=turned.y + dy)):
                return

    def hold(self):
        if self.hold_used:
            return
        previous, self.held = self.held, self.active.kind
        self.spawn(previous, reset_hold=False)
        self.hold_used = True

    def handle(self, key):
        if self.over or self.clear_rows or self.active is None:
            return
        if key in (curses.KEY_LEFT, ord('a'), ord('A')):
            self.manipulate(replace(self.active, x=self.active.x - 1))
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
            self.manipulate(replace(self.active, x=self.active.x + 1))
        elif key in (curses.KEY_UP, ord('w'), ord('W'), ord('x'), ord('X')):
            self.rotate(1)
        elif key in (ord('z'), ord('Z')):
            self.rotate(-1)
        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
            candidate = replace(self.active, y=self.active.y + 1)
            if self.valid(candidate):
                self.active = candidate
                self.score += 1
                self.fall_clock = 0
        elif key == ord(' '):
            destination = self.ghost_y()
            self.score += 2 * (destination - self.active.y)
            self.active.y = destination
            self.lock()
        elif key in (ord('c'), ord('C')):
            self.hold()
        self.best = max(self.best, self.score)

    def lock(self):
        if self.active is None or self.over:
            return
        cells = self.cells()
        if any(y < 0 for x, y in cells):
            self.end_game()
            return
        for x, y in cells:
            self.board[y][x] = self.active.kind
        self.active = None
        self.clear_rows = [y for y, row in enumerate(self.board) if all(row)]
        if self.clear_rows:
            self.clear_elapsed = 0
            count = len(self.clear_rows)
            self.pending_points = (0, 100, 300, 500, 800)[count] * self.level
            self.pending_points += 50 * self.combo * self.level
            self.combo += 1
            self.message = f'{("", "SINGLE", "DOUBLE", "TRIPLE", "TETRIS!")[count]}  +{self.pending_points}'
            self.message_timer = 1.8
        else:
            self.combo = 0
            self.spawn()

    def finish_clear(self):
        count = len(self.clear_rows)
        survivors = [row for y, row in enumerate(self.board) if y not in self.clear_rows]
        self.board = [[None] * WIDTH for _ in range(count)] + survivors
        self.lines += count
        self.score += self.pending_points
        self.best = max(self.best, self.score)
        self.clear_rows = []
        self.clear_elapsed = self.pending_points = 0
        self.spawn()

    def update(self, dt):
        if self.over or dt <= 0:
            return
        # Substeps preserve gravity/lock timing across slow frames.
        remaining = dt
        while remaining > 1e-9 and not self.over:
            step = min(1 / 120, remaining)
            remaining -= step
            self.message_timer = max(0, self.message_timer - step)
            if self.clear_rows:
                self.clear_elapsed += step
                if self.clear_elapsed + 1e-9 >= CLEAR_TIME:
                    self.finish_clear()
                continue
            self.fall_clock += step
            while self.fall_clock >= self.gravity_interval:
                self.fall_clock -= self.gravity_interval
                candidate = replace(self.active, y=self.active.y + 1)
                if self.valid(candidate):
                    self.active = candidate
                else:
                    break
            if self.grounded():
                self.lock_clock += step
                if self.lock_clock + 1e-9 >= LOCK_TIME:
                    self.lock()
            elif self.lock_resets < 12:
                self.lock_clock = 0

    def draw(self, screen):
        screen.centered(0, 'T E T R I S  /  TERMINAL BLOCKS', 1)
        screen.centered(2, '10 x 20   /   CLEAR ROWS TO LEVEL UP', 7)
        left, top = 21, 4
        screen.text(top - 1, left - 1, '+' + '--' * WIDTH + '+', 1)
        screen.text(top + HEIGHT, left - 1, '+' + '--' * WIDTH + '+', 1)
        for y, row in enumerate(self.board):
            screen.text(top + y, left - 1, '|', 1)
            screen.text(top + y, left + WIDTH * 2, '|', 1)
            for x, kind in enumerate(row):
                symbol, color = ('[]', COLORS[kind]) if kind else (' .', 7)
                if y in self.clear_rows:
                    if self.clear_elapsed < .16:
                        symbol, color = '##', 8 if int(self.clear_elapsed * 30) % 2 else 2
                    else:
                        radius = (self.clear_elapsed - .16) / (CLEAR_TIME - .16) * 6
                        symbol, color = ('  ', 7) if abs(x - 4.5) <= radius else ('**', 1)
                screen.text(top + y, left + x * 2, symbol, color)
        if self.active and not self.over:
            for x, y in self.cells(y=self.ghost_y()):
                if y >= 0:
                    screen.text(top + y, left + x * 2, '::', 7)
            for x, y in self.cells():
                if y >= 0:
                    screen.text(top + y, left + x * 2, '[]', COLORS[self.active.kind])

        def preview(kind, row, col):
            if kind:
                for x, y in SHAPES[kind]:
                    screen.text(row + y, col + x * 2, '[]', COLORS[kind])

        for row, label, value in ((4, 'SCORE', self.score), (8, 'LEVEL', self.level),
                                  (11, 'LINES', self.lines), (22, 'BEST', self.best)):
            screen.text(row, 2, label, 7)
            screen.text(row + 1, 2, str(value), 2)
        screen.text(15, 2, 'HOLD' + (' [USED]' if self.hold_used else ' [C]'), 4)
        preview(self.held, 17, 3)
        screen.text(4, 46, 'NEXT', 7)
        for index, kind in enumerate(self.next[:3]):
            preview(kind, 6 + index * 5, 46)
        if self.combo > 1:
            screen.text(22, 46, f'CHAIN {self.combo}', 4)
        screen.centered(26, self.message if self.message_timer > 0 else ':: LANDING GHOST   C: HOLD ONCE PER PIECE', 2)
        screen.text(28, 1, 'A/D or LEFT/RIGHT: Move   UP/W/X: Rotate   Z: Reverse')
        screen.text(29, 1, 'S/DOWN: Soft drop   SPACE: Hard drop   C: Hold')
        screen.text(31, 1, 'ENTER: Start   P: Pause   R: Restart   Q/ESC: Quit', 1)


def main():
    return run(TetrisGame)


if __name__ == '__main__':
    raise SystemExit(main())
