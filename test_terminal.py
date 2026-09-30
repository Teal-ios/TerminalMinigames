"""Real PTY checks for input, screen lifecycle, and restored terminal modes."""
import fcntl
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import time
import unittest

ROOT = Path(__file__).resolve().parent


class TerminalTests(unittest.TestCase):
    def drain(self, fd, seconds=0.15):
        chunks = []
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if select.select([fd], [], [], max(0, end - time.monotonic()))[0]:
                chunks.append(os.read(fd, 65536))
        return b''.join(chunks)

    def until(self, fd, marker):
        output = b''
        deadline = time.monotonic() + 4
        while marker not in output and time.monotonic() < deadline:
            output += self.drain(fd)
        self.assertTrue(marker in output, f'Missing {marker!r}; received {len(output)} bytes, tail={output[-200:]!r}')
        return output

    def test_all_games_accept_input_and_restore_terminal(self):
        for game in ('poop', 'space', 'volley', 'breakout', 'fight', 'tetris'):
            with self.subTest(game=game):
                master, slave = pty.openpty()
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))
                before = termios.tcgetattr(slave)
                process = subprocess.Popen([sys.executable, str(ROOT / 'arcade'), game],
                                           stdin=slave, stdout=slave, stderr=slave,
                                           env=dict(os.environ, TERM='xterm-256color'))
                try:
                    output = self.until(master, b'TO START')
                    os.write(master, b'\rad')
                    output += self.drain(master)
                    if game == 'fight':
                        os.write(master, b'a')
                        # Curses may retain the leading G from the previous GAP label.
                        output += self.until(master, b'STRIKES BLOCKED')
                    elif game == 'tetris':
                        os.write(master, b'wzsc ')
                        output += self.drain(master)
                    os.write(master, b'p')
                    output += self.until(master, b'PAUSED')
                    os.write(master, b'r')
                    output += self.drain(master)
                    os.write(master, b'q')
                    output += self.drain(master)
                    self.assertEqual(process.wait(timeout=4), 0)
                    self.assertNotIn(b'Traceback', output)
                    # macOS may set PENDIN (retype pending input) on a PTY.
                    # Compare the actual input modes, not that transient flag.
                    mask = termios.ECHO | termios.ICANON | termios.ISIG | termios.IEXTEN
                    self.assertEqual(before[3] & mask, termios.tcgetattr(slave)[3] & mask)
                finally:
                    if process.poll() is None:
                        os.write(master, b'q')
                        self.drain(master)
                        try:
                            process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                    os.close(master)
                    os.close(slave)

    def test_resize_pauses_and_recovers(self):
        for game in ('poop', 'space', 'volley', 'breakout', 'fight', 'tetris'):
            with self.subTest(game=game):
                master, slave = pty.openpty()
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 15, 35, 0, 0))
                process = subprocess.Popen([sys.executable, str(ROOT / 'games' / game / 'game.py')],
                                           stdin=slave, stdout=slave, stderr=slave,
                                           env=dict(os.environ, TERM='xterm-256color'))
                try:
                    self.until(master, b'terminal')
                    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))
                    os.kill(process.pid, signal.SIGWINCH)
                    self.until(master, b'TO START')
                    os.write(master, b'q')
                    self.drain(master)
                    self.assertEqual(process.wait(timeout=4), 0)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    os.close(master)
                    os.close(slave)
