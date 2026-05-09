from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from bot.game_state import GameState, Entity
from bot.geometry import (
    distance, weighted_flee_vector, move_away_from,
    point_in_radius, nearest_entity
)


@dataclass
class Action:
    move_target: Optional[tuple] = None
    stop_moving: bool = False
    shoot_target: Optional[tuple] = None
    use_super_at: Optional[tuple] = None
    reason: str = ""


class ShowdownStrategy:
    def __init__(self, config: dict):
        cfg = config["strategy"]
        self.dodge_radius = cfg["projectile_dodge_radius_px"]
        self.poison_margin = cfg["poison_safety_margin_px"]
        self.cube_radius = cfg["collect_cube_radius_px"]
        self.engage_min_hp = cfg["engage_min_hp_pct"]
        self.shoot_range = cfg["shoot_range_px"]
        self.super_min_enemies = cfg["super_min_enemies_nearby"]
        self._screen_region: Optional[dict] = None

    def set_screen_region(self, region: dict) -> None:
        self._screen_region = region

    def decide(self, state: GameState) -> Action:
        for handler in (
            self._dodge_projectiles,
            self._flee_poison,
            self._collect_power_cube,
            self._engage_enemy,
        ):
            action = handler(state)
            if action is not None:
                return action
        return self._explore(state)

    def _dodge_projectiles(self, state: GameState) -> Optional[Action]:
        pos = state.player_pos
        if pos is None:
            return None
        threats = [
            e for e in state.incoming_projectiles
            if point_in_radius((e.bbox.cx, e.bbox.cy), pos, self.dodge_radius)
        ]
        if not threats:
            return None
        centers = [(e.bbox.cx, e.bbox.cy) for e in threats]
        weights = [e.bbox.confidence for e in threats]
        vx, vy = weighted_flee_vector(pos, centers, weights)
        flee_dist = self.dodge_radius * 2
        target = (pos[0] + vx * flee_dist, pos[1] + vy * flee_dist)
        return Action(move_target=target, reason="dodge_projectile")

    def _flee_poison(self, state: GameState) -> Optional[Action]:
        pos = state.player_pos
        if pos is None or not state.poison_zones:
            return None
        for poison in state.poison_zones:
            pcx, pcy = poison.bbox.cx, poison.bbox.cy
            pw, ph = poison.bbox.w / 2, poison.bbox.h / 2
            in_poison = (
                abs(pos[0] - pcx) < pw + self.poison_margin
                and abs(pos[1] - pcy) < ph + self.poison_margin
            )
            if in_poison:
                flee_target = move_away_from(pos, (pcx, pcy), self.poison_margin * 3)
                return Action(move_target=flee_target, reason="flee_poison")
        return None

    def _collect_power_cube(self, state: GameState) -> Optional[Action]:
        pos = state.player_pos
        cube = state.nearest_power_cube
        if pos is None or cube is None:
            return None
        cube_pos = (cube.bbox.cx, cube.bbox.cy)
        if distance(pos, cube_pos) > self.cube_radius:
            return None
        # Shoot any enemy that is between us and the cube
        nearest_enemy = state.nearest_enemy
        if nearest_enemy is not None:
            enemy_pos = (nearest_enemy.bbox.cx, nearest_enemy.bbox.cy)
            if distance(pos, enemy_pos) < self.shoot_range:
                return Action(
                    move_target=cube_pos,
                    shoot_target=enemy_pos,
                    reason="collect_cube_shoot_enemy",
                )
        return Action(move_target=cube_pos, reason="collect_cube")

    def _engage_enemy(self, state: GameState) -> Optional[Action]:
        pos = state.player_pos
        enemy = state.nearest_enemy
        if pos is None or enemy is None:
            return None
        if self._estimate_player_hp(state) < self.engage_min_hp:
            return None
        enemy_pos = (enemy.bbox.cx, enemy.bbox.cy)
        dist = distance(pos, enemy_pos)

        # Check if super is ready and enough enemies nearby
        enemies_nearby = sum(
            1 for e in state.enemies
            if distance(pos, (e.bbox.cx, e.bbox.cy)) < self.shoot_range
        )
        if self._is_super_ready(state) and enemies_nearby >= self.super_min_enemies:
            return Action(
                stop_moving=True,
                use_super_at=enemy_pos,
                reason="use_super",
            )

        if dist > self.shoot_range:
            return Action(move_target=enemy_pos, reason="chase_enemy")

        # In range: stop and shoot
        return Action(stop_moving=True, shoot_target=enemy_pos, reason="shoot_enemy")

    def _explore(self, state: GameState) -> Action:
        pos = state.player_pos
        if pos is None:
            return Action(reason="no_player_visible")

        nearest_box = nearest_entity(pos, state.boxes)
        if nearest_box is not None:
            return Action(
                move_target=(nearest_box.bbox.cx, nearest_box.bbox.cy),
                reason="explore_to_box",
            )

        # Drift toward screen center if nothing visible
        center = self._screen_center_fallback()
        return Action(move_target=center, reason="explore_to_center")

    def _estimate_player_hp(self, state: GameState) -> float:
        pos = state.player_pos
        if pos is None or not state.live_bars or state.player is None:
            return 1.0
        # Closest live_bar to player
        bar = nearest_entity(pos, state.live_bars)
        if bar is None:
            return 1.0
        full_width = state.player.bbox.w
        if full_width <= 0:
            return 1.0
        return min(1.0, bar.bbox.w / full_width)

    def _is_super_ready(self, state: GameState) -> bool:
        # Placeholder: super detection not yet implemented
        return False

    def _screen_center_fallback(self) -> tuple:
        if self._screen_region is not None:
            from bot.geometry import screen_center
            return screen_center(self._screen_region)
        return (320.0, 240.0)
