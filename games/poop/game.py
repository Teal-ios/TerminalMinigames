#!/usr/bin/env python3
"""A tiny terminal dodge game. Run with python3 poop_dodge.py."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


import curses
import random
import sys
import time


WIDTH, HEIGHT = 40, 20
MIN_COLS, MIN_ROWS = 48, 29


class Game:
    def __init__(self):
        self.player = WIDTH // 2
        self.drops = []
        self.elapsed = 0.0
        self.spawn_clock = 0.0
        self.over = False

    @property
    def score(self):
        return int(self.elapsed * 10)

    @property
    def level(self):
        return 1 + int(self.elapsed // 12)

    def move(self, direction):
        if not self.over:
            self.player = max(0, min(WIDTH - 1, self.player + direction))
            self.check_collision()

    def check_collision(self):
        self.over = any(x == self.player and int(y) == HEIGHT - 1
                        for x, y in self.drops)

    def update(self, dt):
        if self.over:
            return
        self.elapsed += dt
        speed = min(14.0, 4.0 + self.level * 0.8)
        # Check swept positions so a slow frame cannot skip a collision.
        for x, y in self.drops:
            if x == self.player and y < HEIGHT and y + speed * dt >= HEIGHT - 1:
                self.over = True
        self.drops = [(x, y + speed * dt) for x, y in self.drops
                      if y + speed * dt < HEIGHT]
        if self.over:
            return
        self.spawn_clock += dt
        interval = max(0.10, 0.55 - (self.level - 1) * 0.045)
        while self.spawn_clock >= interval:
            self.spawn_clock -= interval
            self.drops.append((random.randrange(WIDTH), 0.0))


def play(screen):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    screen.keypad(True)
    screen.nodelay(True)
    colors = [0, 0, 0, 0]
    if curses.has_colors():
        curses.start_color()
        for number, color in enumerate(
                (curses.COLOR_CYAN, curses.COLOR_YELLOW, curses.COLOR_RED), 1):
            curses.init_pair(number, color, curses.COLOR_BLACK)
            colors[number] = curses.color_pair(number)

    game = Game()
    best = 0
    paused = False
    started = False
    last = time.monotonic()

    def put(y, x, text, style=0):
        try:
            screen.addstr(y, x, text, style)
        except curses.error:
            pass  # A terminal resize may happen halfway through drawing.

    while True:
        now = time.monotonic()
        dt = min(now - last, 0.05)
        last = now
        rows, cols = screen.getmaxyx()
        too_small = rows < MIN_ROWS or cols < MIN_COLS
        key = screen.getch()
        if key in (ord('q'), ord('Q'), 27):
            return
        if not too_small:
            if key in (10, 13, ord(' ')) and not started:
                started = True
            elif key in (ord('r'), ord('R')):
                best = max(best, game.score)
                game = Game()
                paused = False
                started = True
            elif key in (ord('p'), ord('P'), ord(' ')) and started and not game.over:
                paused = not paused
            elif started and not paused:
                if key in (curses.KEY_LEFT, ord('a'), ord('A')):
                    game.move(-1)
                elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
                    game.move(1)
            if started and not paused:
                game.update(dt)
            best = max(best, game.score)

        screen.erase()
        if too_small:
            put(0, 0, 'Please enlarge the terminal.')
            put(1, 0, 'Need 48 columns x 29 rows. Q: quit')
            screen.refresh()
            time.sleep(0.03)
            continue

        left = (cols - WIDTH - 2) // 2
        top = (rows - MIN_ROWS) // 2
        put(top, left + 10, 'P O O P   D O D G E', colors[1] | curses.A_BOLD)
        put(top + 2, left, f'SCORE {game.score:5}   BEST {best:5}   LV {game.level}')
        put(top + 3, left, '+' + '-' * WIDTH + '+', colors[1])
        for y in range(HEIGHT):
            put(top + 4 + y, left, '|', colors[1])
            put(top + 4 + y, left + WIDTH + 1, '|', colors[1])
        put(top + 4 + HEIGHT, left, '+' + '-' * WIDTH + '+', colors[1])
        for x, y in game.drops:
            put(top + 4 + int(y), left + 1 + x, '*', colors[2] | curses.A_BOLD)
        put(top + 3 + HEIGHT, left + 1 + game.player, '@',
            colors[3 if game.over else 1] | curses.A_BOLD)

        message = None
        if not started:
            message = ' ENTER / SPACE TO START '
        elif game.over:
            message = ' SPLAT!  R: RETRY  Q: QUIT '
        elif paused:
            message = ' PAUSED - SPACE TO RESUME '
        if message:
            put(top + 4 + HEIGHT // 2, left + 1 + (WIDTH - len(message)) // 2,
                message, curses.A_REVERSE | curses.A_BOLD)

        put(top + 25, left, 'Move: LEFT/RIGHT or A/D   You: @  Poop: *')
        put(top + 26, left, 'SPACE/P: Pause   R: Restart   Q/ESC: Quit')
        screen.refresh()
        time.sleep(1 / 60)


def main():
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print('Run in an interactive terminal: python3 poop_dodge.py')
        return 1
    try:
        curses.wrapper(play)
    except KeyboardInterrupt:
        pass
    except curses.error as error:
        print(f'Terminal could not start the game: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
