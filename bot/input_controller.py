from __future__ import annotations
import math
import subprocess
from typing import Optional

from bot.geometry import angle_to, quantize_direction


_DIRECTION_KEYS: dict = {
    (1,  0):  ["d"],
    (-1, 0):  ["a"],
    (0, -1):  ["w"],
    (0,  1):  ["s"],
    (1, -1):  ["w", "d"],
    (-1, -1): ["w", "a"],
    (1,  1):  ["s", "d"],
    (-1, 1):  ["s", "a"],
    (0,  0):  [],
}


class InputController:
    def __init__(self, config: dict):
        self._cfg = config["input"]
        self._backend = self._cfg.get("backend", "pynput")
        self._held: set = set()
        self._kb = None
        self._mouse = None
        self._init_backend()

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

    def move_toward(self, target: tuple, player_pos: tuple) -> None:
        if player_pos is None:
            return
        ang = angle_to(player_pos, target)
        direction = quantize_direction(ang)
        keys = _DIRECTION_KEYS.get(direction, [])
        self._set_held_keys(set(keys))

    def stop_moving(self) -> None:
        self._set_held_keys(set())

    def aim_at(self, screen_x: float, screen_y: float) -> None:
        x, y = int(screen_x), int(screen_y)
        if self._backend == "pynput" and self._mouse:
            self._mouse.position = (x, y)
        else:
            subprocess.run(
                ["xdotool", "mousemove", "--screen", "0", str(x), str(y)],
                check=False, capture_output=True
            )

    def shoot(self, screen_x: float, screen_y: float) -> None:
        self.aim_at(screen_x, screen_y)
        if self._backend == "pynput" and self._mouse:
            self._mouse.click(self._Button.left)
        else:
            subprocess.run(["xdotool", "click", "1"], check=False, capture_output=True)

    def use_super(self, screen_x: float, screen_y: float) -> None:
        self.aim_at(screen_x, screen_y)
        super_key = self._cfg.get("super_key", "f")
        self._press_key(super_key)

    def release_all(self) -> None:
        self._set_held_keys(set())

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

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
            self._kb.press(key)
        else:
            subprocess.run(
                ["xdotool", "keydown", key], check=False, capture_output=True
            )

    def _key_up(self, key: str) -> None:
        if self._backend == "pynput" and self._kb:
            self._kb.release(key)
        else:
            subprocess.run(
                ["xdotool", "keyup", key], check=False, capture_output=True
            )

    def _press_key(self, key: str) -> None:
        if self._backend == "pynput" and self._kb:
            self._kb.press(key)
            self._kb.release(key)
        else:
            subprocess.run(
                ["xdotool", "key", key], check=False, capture_output=True
            )
