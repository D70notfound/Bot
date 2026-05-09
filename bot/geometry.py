import math
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from bot.game_state import Entity


def distance(a: tuple, b: tuple) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def angle_to(origin: tuple, target: tuple) -> float:
    """Angle in degrees from origin to target. 0=right, 90=up (screen coords: y increases downward)."""
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    return math.degrees(math.atan2(-dy, dx)) % 360


def nearest_entity(ref: tuple, entities: list) -> Optional["Entity"]:
    if not entities:
        return None
    return min(entities, key=lambda e: distance(ref, (e.bbox.cx, e.bbox.cy)))


def point_in_radius(point: tuple, center: tuple, radius: float) -> bool:
    return distance(point, center) <= radius


def move_away_from(origin: tuple, threat: tuple, dist: float) -> tuple:
    """Return a point `dist` pixels from origin, on the far side away from threat."""
    dx = origin[0] - threat[0]
    dy = origin[1] - threat[1]
    length = math.hypot(dx, dy) or 1.0
    return (origin[0] + dx / length * dist, origin[1] + dy / length * dist)


def weighted_flee_vector(origin: tuple, threats: list, weights: list) -> tuple:
    """
    Weighted sum of unit vectors pointing away from each threat.
    Returns normalized (dx, dy). Returns (0, -1) (move up) if no threats.
    """
    if not threats:
        return (0.0, -1.0)
    vx, vy = 0.0, 0.0
    for threat, w in zip(threats, weights):
        dx = origin[0] - threat[0]
        dy = origin[1] - threat[1]
        length = math.hypot(dx, dy) or 1.0
        vx += (dx / length) * w
        vy += (dy / length) * w
    length = math.hypot(vx, vy) or 1.0
    return (vx / length, vy / length)


def screen_center(region: dict) -> tuple:
    return (region["left"] + region["width"] / 2, region["top"] + region["height"] / 2)


def quantize_direction(angle_deg: float) -> tuple:
    """
    Map a continuous angle (0=right, 90=up) to one of 8 (dx, dy) sign pairs.
    Screen coords: +y is down, so 'up' in game = negative screen-y.
    """
    sector = int((angle_deg + 22.5) % 360 / 45)
    mapping = [
        (1, 0),   # 0: E
        (1, -1),  # 1: NE
        (0, -1),  # 2: N
        (-1, -1), # 3: NW
        (-1, 0),  # 4: W
        (-1, 1),  # 5: SW
        (0, 1),   # 6: S
        (1, 1),   # 7: SE
    ]
    return mapping[sector]
