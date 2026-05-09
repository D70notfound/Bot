from __future__ import annotations
import platform
import subprocess
import sys
from typing import Optional

import mss
import numpy as np


class WindowNotFoundError(Exception):
    pass


class ScreenCapture:
    def __init__(self, config: dict):
        self._title = config["emulator"]["window_title"]
        self._override_region = config["emulator"].get("capture_region")
        self._sct = mss.mss()
        self._region: Optional[dict] = None

    def find_window(self) -> dict:
        if self._override_region:
            self._region = self._override_region
            return self._region

        region = None
        if platform.system() == "Windows":
            region = self._find_window_windows()
        else:
            region = self._find_window_linux()

        if region is None:
            raise WindowNotFoundError(
                f"Could not find emulator window: '{self._title}'. "
                "Set 'capture_region' in config.json to override."
            )
        self._region = region
        return region

    def _find_window_windows(self) -> Optional[dict]:
        try:
            import pygetwindow as gw
            wins = gw.getWindowsWithTitle(self._title)
            if not wins:
                return None
            w = wins[0]
            return {"left": w.left, "top": w.top, "width": w.width, "height": w.height}
        except Exception:
            return None

    def _find_window_linux(self) -> Optional[dict]:
        try:
            out = subprocess.check_output(
                ["wmctrl", "-lG"], text=True, stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            # wmctrl not installed — fall back to full screen[0]
            monitor = self._sct.monitors[1]
            return {
                "left": monitor["left"],
                "top": monitor["top"],
                "width": monitor["width"],
                "height": monitor["height"],
            }
        except subprocess.CalledProcessError:
            return None

        title_lower = self._title.lower()
        for line in out.splitlines():
            parts = line.split(None, 7)
            if len(parts) < 8:
                continue
            title = parts[7].lower()
            if title_lower in title:
                try:
                    x, y, w, h = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
                    return {"left": x, "top": y, "width": w, "height": h}
                except ValueError:
                    continue
        return None

    def grab_frame(self) -> np.ndarray:
        if self._region is None:
            raise RuntimeError("Call find_window() before grab_frame()")
        screenshot = self._sct.grab(self._region)
        # mss returns BGRA; convert to BGR
        frame = np.array(screenshot)[:, :, :3]
        return frame

    def resize_for_api(
        self, frame: np.ndarray, max_dim: int = 640
    ) -> tuple:
        h, w = frame.shape[:2]
        if max(h, w) <= max_dim:
            return frame, 1.0, 1.0
        scale = max_dim / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        import cv2
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        return resized, w / new_w, h / new_h
