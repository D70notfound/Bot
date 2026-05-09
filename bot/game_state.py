from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Optional

from bot.geometry import distance


@dataclass
class BBox:
    cx: float
    cy: float
    w: float
    h: float
    confidence: float

    @property
    def top_left(self) -> tuple:
        return (self.cx - self.w / 2, self.cy - self.h / 2)

    @property
    def area(self) -> float:
        return self.w * self.h

    @property
    def center(self) -> tuple:
        return (self.cx, self.cy)


@dataclass
class Entity:
    bbox: BBox
    cls: str


@dataclass
class GameState:
    player: Optional[Entity] = None
    enemies: list = field(default_factory=list)
    teammates: list = field(default_factory=list)
    power_cubes: list = field(default_factory=list)
    boxes: list = field(default_factory=list)
    bushes: list = field(default_factory=list)
    walls: list = field(default_factory=list)
    projectiles: list = field(default_factory=list)
    shot_predictions: list = field(default_factory=list)
    munitions: list = field(default_factory=list)
    poison_zones: list = field(default_factory=list)
    live_bars: list = field(default_factory=list)
    frame_id: int = 0
    timestamp: float = field(default_factory=time.time)

    @property
    def player_pos(self) -> Optional[tuple]:
        if self.player is None:
            return None
        return (self.player.bbox.cx, self.player.bbox.cy)

    @property
    def nearest_enemy(self) -> Optional[Entity]:
        pos = self.player_pos
        if pos is None or not self.enemies:
            return None
        return min(self.enemies, key=lambda e: distance(pos, (e.bbox.cx, e.bbox.cy)))

    @property
    def nearest_power_cube(self) -> Optional[Entity]:
        pos = self.player_pos
        if pos is None or not self.power_cubes:
            return None
        return min(self.power_cubes, key=lambda e: distance(pos, (e.bbox.cx, e.bbox.cy)))

    @property
    def incoming_projectiles(self) -> list:
        pos = self.player_pos
        if pos is None:
            return []
        threats = self.projectiles + self.shot_predictions
        return [e for e in threats if distance(pos, (e.bbox.cx, e.bbox.cy)) < 200]


CLASS_MAP = {
    "player": "player",
    "enemy": "enemies",
    "teammate": "teammates",
    "power_cube": "power_cubes",
    "box": "boxes",
    "bush": "bushes",
    "wall": "walls",
    "projectile": "projectiles",
    "shot_prodiktion": "shot_predictions",
    "munition": "munitions",
    "poison": "poison_zones",
    "live_bar": "live_bars",
}


class GameStateParser:
    def parse(
        self,
        raw_detections: list,
        scale_x: float,
        scale_y: float,
        frame_id: int = 0,
        timestamp: float = 0.0,
    ) -> GameState:
        state = GameState(frame_id=frame_id, timestamp=timestamp)
        lists: dict = {
            "enemies": state.enemies,
            "teammates": state.teammates,
            "power_cubes": state.power_cubes,
            "boxes": state.boxes,
            "bushes": state.bushes,
            "walls": state.walls,
            "projectiles": state.projectiles,
            "shot_predictions": state.shot_predictions,
            "munitions": state.munitions,
            "poison_zones": state.poison_zones,
            "live_bars": state.live_bars,
        }

        for det in raw_detections:
            cls = det.get("class", "")
            field_name = CLASS_MAP.get(cls)
            if field_name is None:
                continue

            bbox = BBox(
                cx=det["x"] * scale_x,
                cy=det["y"] * scale_y,
                w=det["width"] * scale_x,
                h=det["height"] * scale_y,
                confidence=det.get("confidence", 1.0),
            )
            entity = Entity(bbox=bbox, cls=cls)

            if field_name == "player":
                state.player = entity
            else:
                lists[field_name].append(entity)

        return state
