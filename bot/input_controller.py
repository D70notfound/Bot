from __future__ import annotations
import subprocess
from typing import Optional

from bot.geometry import angle_to, quantize_direction


_DEFAULT_MOVEMENT_KEYS = {"up": "w", "down": "s", "left": "a", "right": "d"}


class InputController:
    def __init__(self, config: dict):
        self._cfg = config["input"]
        self._backend = self._cfg.get("backend", "pynput")
        self._held: set = set()
        self._kb = None
        self._mouse = None
        self._Key = None
        self._Button = None
        self._region_left = 0
        self._region_top = 0
        self._direction_keys = self._build_direction_keys(
            self._cfg.get("movement_keys", _DEFAULT_MOVEMENT_KEYS)
        )
        self._init_backend()

    @staticmethod
    def _build_direction_keys(km: dict) -> dict:
        up = km.get("up", "w")
        down = km.get("down", "s")
        left = km.get("left", "a")
        right = km.get("right", "d")
        return {
            (1,  0):  [right],
            (-1, 0):  [left],
            (0, -1):  [up],
            (0,  1):  [down],
            (1, -1):  [up, right],
            (-1, -1): [up, left],
            (1,  1):  [down, right],
            (-1, 1):  [down, left],
            (0,  0):  [],
        }

    def _init_backend(self) -> None:
        if self._backend == "pynput":
            try:
                from pynput.keyboard import Controller as KbCtrl, Key
                from pynput.mouse import Controller as MouseCtrl, Button
                self._kb = KbCtrl()
                self._mouse = MouseCtrl()
                self._Key = Key
                self._Button = Button
            except Exception:
                self._backend = "xdotool"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_region(self, region: dict) -> None:
        """Capture region in absolute screen coords; used to map detection
        coordinates (frame-local, origin at region top-left) to absolute
        screen coordinates for mouse aiming."""
        self._region_left = int(region.get("left", 0))
        self._region_top = int(region.get("top", 0))

    def move_toward(self, target: tuple, player_pos: Optional[tuple]) -> None:
        if player_pos is None or target is None:
            return
        ang = angle_to(player_pos, target)
        direction = quantize_direction(ang)
        keys = self._direction_keys.get(direction, [])
        self._set_held_keys(set(keys))

    def stop_moving(self) -> None:
        self._set_held_keys(set())

    def aim_at(self, frame_x: float, frame_y: float) -> None:
        x, y = self._to_absolute(frame_x, frame_y)
        if self._backend == "pynput" and self._mouse:
            self._mouse.position = (x, y)
        else:
            subprocess.run(
                ["xdotool", "mousemove", "--screen", "0", str(x), str(y)],
                check=False, capture_output=True,
            )

    def shoot(self, frame_x: float, frame_y: float) -> None:
        self.aim_at(frame_x, frame_y)
        if self._backend == "pynput" and self._mouse and self._Button:
            self._mouse.click(self._Button.left)
        else:
            subprocess.run(["xdotool", "click", "1"], check=False, capture_output=True)

    def use_super(self, frame_x: float, frame_y: float) -> None:
        self.aim_at(frame_x, frame_y)
        super_key = self._cfg.get("super_key", "f")
        self._press_key(super_key)

    def release_all(self) -> None:
        self._set_held_keys(set())

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _to_absolute(self, frame_x: float, frame_y: float) -> tuple:
        return (int(frame_x) + self._region_left, int(frame_y) + self._region_top)

    def _set_held_keys(self, desired: set) -> None:
        to_release = self._held - desired
        to_press = desired - self._held
        for k in to_release:
            self._key_up(k)
        for k in to_press:
            self._key_down(k)
        self._held = desired

    def _key_down(self, key: str) -> None:
        if self._backend == "pynput" and self._kb:
            self._kb.press(self._resolve_key(key))
        else:
            subprocess.run(["xdotool", "keydown", key], check=False, capture_output=True)

    def _key_up(self, key: str) -> None:
        if self._backend == "pynput" and self._kb:
            self._kb.release(self._resolve_key(key))
        else:
            subprocess.run(["xdotool", "keyup", key], check=False, capture_output=True)

    def _press_key(self, key: str) -> None:
        if self._backend == "pynput" and self._kb:
            resolved = self._resolve_key(key)
            self._kb.press(resolved)
            self._kb.release(resolved)
        else:
            subprocess.run(["xdotool", "key", key], check=False, capture_output=True)

    def _resolve_key(self, key: str):
        """Map a string like 'space' or 'f' to a pynput Key or single char."""
        if self._Key is None or len(key) == 1:
            return key
        return getattr(self._Key, key, key)
