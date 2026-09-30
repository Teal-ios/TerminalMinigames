"""Compatibility entry point; prefer ./arcade poop."""
from games.poop.game import main

if __name__ == "__main__":
    raise SystemExit(main())
