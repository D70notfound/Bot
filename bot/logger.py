from __future__ import annotations
import json
import logging
import os
import time
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from bot.game_state import GameState
    from bot.strategy import Action


class BotLogger:
    def __init__(self, config: dict):
        dbg = config.get("debug", {})
        self._save_frames = dbg.get("save_frames", False)
        self._frames_dir = dbg.get("frames_dir", "debug_frames")

        handler = RotatingFileHandler(
            "bot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        self._log = logging.getLogger("bot")
        self._log.setLevel(logging.DEBUG)
        if not self._log.handlers:
            self._log.addHandler(handler)

        if self._save_frames:
            os.makedirs(self._frames_dir, exist_ok=True)

    def log_tick(
        self,
        frame_id: int,
        state: "GameState",
        action: "Action",
        inference_ms: float,
        loop_ms: float,
    ) -> None:
        record = {
            "frame": frame_id,
            "t": round(time.time(), 3),
            "action": action.reason,
            "enemies": len(state.enemies),
            "cubes": len(state.power_cubes),
            "projectiles": len(state.projectiles),
            "player": list(state.player_pos) if state.player_pos else None,
            "infer_ms": round(inference_ms, 1),
            "loop_ms": round(loop_ms, 1),
        }
        self._log.info(json.dumps(record))

    def save_debug_frame(self, frame: "np.ndarray", frame_id: int) -> None:
        if not self._save_frames:
            return
        import cv2
        path = os.path.join(self._frames_dir, f"{frame_id:06d}.jpg")
        cv2.imwrite(path, frame)
