"""Original move sets for three terminal stick fighters (seconds/cells)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    name: str
    damage: int
    reach: float
    startup: float
    recovery: float = 0.28
    stun: float = 0.34
    height: str = 'mid'
    push: float = 0.6
    launch: float = 0
    down: bool = False
    cost: int = 0
    hits: int = 1
    advance: float = 0
    projectile: float = 0
    armor: bool = False
    breaker: bool = False
    active: float = 0.10

    @property
    def last_hit(self):
        return self.startup + (self.hits - 1) * 0.12

    @property
    def duration(self):
        return self.last_hit + self.active + self.recovery


BASIC = {
    'j': Move('JAB', 6, 5.5, 0.08, recovery=0.18, height='high', push=0.15),
    'k': Move('HEAVY', 12, 6, 0.20, push=1.2),
    'l': Move('SIDE KICK', 9, 7, 0.13, push=0.4),
    'u': Move('LAUNCHER', 10, 5.5, 0.24, recovery=0.42, launch=14, push=0.1),
    'o': Move('THROW', 20, 4.8, 0.15, recovery=0.40, height='grab', down=True),
}
SWEEP = Move('LOW SWEEP', 10, 6.5, 0.22, height='low', down=True, recovery=0.38)
AIR_KICK = Move('FLYING KICK', 11, 7, 0.13, push=1.0)
CHAINS = {
    'jjk': Move('RUSH FINISH', 15, 7, 0.12, push=2.0),
    'jlk': Move('SPIN LAUNCH', 12, 7.5, 0.12, launch=13, push=0.2),
    'llk': Move('AXE FINISH', 17, 8, 0.15, down=True, push=2.0),
}


@dataclass(frozen=True)
class Profile:
    name: str
    hp: int
    speed: float
    power: float
    description: str
    skills: dict
    reach_scale: float = 1.0
    concept: str = ''
    color: int = 1


ROSTER = (
    Profile('STRIKER', 100, 1.0, 1.0, 'Balanced: launchers, palm strikes, wave', {
        'i': Move('PALM BURST', 18, 7.5, 0.18, cost=20, push=2),
        'z': Move('RISING FIST', 14, 6, 0.20, cost=30, launch=16, push=0.1),
        'x': Move('SONIC WAVE', 16, 60, 0.24, cost=35, projectile=26),
        'c': Move('METEOR KICK', 26, 7, 0.32, cost=50, advance=18, down=True, breaker=True),
        'h': Move('DRAGON STORM', 13, 8, 0.25, cost=100, hits=3, down=True, push=0.2),
    }, concept='EMBER / spiked hair + red headband', color=1),
    Profile('RUSH', 90, 1.3, 0.9, 'Fast: dashes, multi-hit attacks, pressure', {
        'i': Move('FLASH STEP', 13, 6, 0.10, cost=20, advance=28, recovery=0.16),
        'z': Move('CYCLONE KICK', 9, 7, 0.16, cost=30, hits=2, launch=12, push=0.1),
        'x': Move('NEEDLE WAVE', 14, 60, 0.15, cost=35, projectile=34),
        'c': Move('PHANTOM RUSH', 9, 8, 0.12, cost=50, hits=4, advance=22, push=0.1),
        'h': Move('SHADOW DANCE', 11, 9, 0.16, cost=100, hits=5, down=True, push=0.1),
    }, reach_scale=0.94, concept='GALE / ponytail + flowing scarf', color=4),
    Profile('IRON', 120, 0.8, 1.1, 'Power: armored shoulder, low wave, grabs', {
        'i': Move('IRON SHOULDER', 23, 6.5, 0.34, cost=20, advance=15, armor=True, push=2),
        'z': Move('QUAKE FIST', 20, 7, 0.30, cost=30, height='low', down=True),
        'x': Move('EARTH WAVE', 20, 60, 0.32, cost=35, height='low', projectile=20),
        'c': Move('TITAN CLINCH', 32, 6, 0.22, cost=50, height='grab', down=True),
        'h': Move('METEOR SLAM', 45, 6.5, 0.25, cost=100, height='grab', down=True),
    }, reach_scale=1.08, concept='ANVIL / mohawk + heavy gauntlets', color=2),
)
