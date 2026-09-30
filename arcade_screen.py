"""Small shared terminal lifecycle; games own their rules and rendering."""
import curses
import sys
import time


class Screen:
    def __init__(self, window, width, height):
        self.window, self.width, self.height = window, width, height
        self.left = self.top = 0
        self.styles = [curses.A_NORMAL] * 5
        if curses.has_colors():
            curses.start_color()
            for index, color in enumerate((curses.COLOR_CYAN, curses.COLOR_YELLOW,
                                            curses.COLOR_RED, curses.COLOR_GREEN), 1):
                curses.init_pair(index, color, curses.COLOR_BLACK)
                self.styles[index] = curses.color_pair(index) | curses.A_BOLD

    def text(self, y, x, value, color=0):
        try:
            self.window.addstr(self.top + y, self.left + x, str(value), self.styles[color])
        except curses.error:
            pass

    def centered(self, y, value, color=0):
        self.text(y, max(0, (self.width - len(value)) // 2), value, color)

    def border(self, y, height):
        self.text(y, 0, '+' + '-' * (self.width - 2) + '+', 1)
        for row in range(1, height - 1):
            self.text(y + row, 0, '|', 1)
            self.text(y + row, self.width - 1, '|', 1)
        self.text(y + height - 1, 0, '+' + '-' * (self.width - 2) + '+', 1)


def run(factory, width=64, height=32):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print('키보드 입력이 가능한 터미널에서 실행하세요.', file=sys.stderr)
        return 1

    def loop(window):
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        window.nodelay(True)
        window.keypad(True)
        canvas = Screen(window, width, height)
        game, started, paused = factory(), False, False
        last = time.monotonic()
        while True:
            now = time.monotonic()
            dt, last = min(0.05, now - last), now
            rows, cols = window.getmaxyx()
            small = rows < height + 1 or cols < width + 2
            key = window.getch()
            if key in (ord('q'), ord('Q'), 27):
                return
            if not small:
                if key in (10, 13) and not started:
                    started = True
                elif key in (ord('r'), ord('R')):
                    game, started, paused = factory(), True, False
                elif key in (ord('p'), ord('P')) and started and not game.over:
                    paused = not paused
                elif started and not paused and not game.over:
                    game.handle(key)
                if started and not paused and not game.over:
                    game.update(dt)
            window.erase()
            if small:
                canvas.left = canvas.top = 0
                canvas.text(0, 0, f'Enlarge terminal to {width + 2} columns x {height + 1} rows.')
                canvas.text(1, 0, 'Game paused. Q: quit')
            else:
                canvas.left, canvas.top = (cols - width) // 2, (rows - height) // 2
                game.draw(canvas)
                if not started:
                    canvas.centered(14, '  ENTER TO START  ', 2)
                elif paused:
                    canvas.centered(14, '  PAUSED - P TO RESUME  ', 2)
                elif game.over:
                    canvas.centered(14, f'  {game.result}  ', 3)
                    canvas.centered(16, '  R: RESTART   Q: QUIT  ', 2)
            window.refresh()
            time.sleep(1 / 60)

    try:
        curses.wrapper(loop)
    except KeyboardInterrupt:
        pass
    except curses.error as error:
        print(f'터미널 초기화 실패: {error}', file=sys.stderr)
        return 1
    return 0
