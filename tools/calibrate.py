#!/usr/bin/env python3
"""
Calibration tool: find emulator window, grab one frame,
call Roboflow API synchronously, annotate and save result.

Usage:
    python tools/calibrate.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import numpy as np

from bot.capture import ScreenCapture, WindowNotFoundError
from bot.detection import RoboflowDetector
from bot.game_state import GameStateParser


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def main():
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    config = load_config(config_path)

    # 1. Find window
    capture = ScreenCapture(config)
    try:
        region = capture.find_window()
        print(f"[+] Window found: {region}")
    except WindowNotFoundError as e:
        print(f"[!] {e}")
        sys.exit(1)

    # 2. Grab frame
    frame = capture.grab_frame()
    cv2.imwrite("calibrate_frame.jpg", frame)
    print(f"[+] Frame saved: calibrate_frame.jpg  ({frame.shape[1]}x{frame.shape[0]})")

    # 3. Resize + infer
    resized, scale_x, scale_y = capture.resize_for_api(frame)
    print(f"[+] Resized to {resized.shape[1]}x{resized.shape[0]} (scale {scale_x:.2f}x{scale_y:.2f})")

    detector = RoboflowDetector(config)
    if not config["roboflow"]["api_key"]:
        print("[!] No API key in config.json — skipping inference. Fill in roboflow.api_key first.")
        sys.exit(0)

    print("[+] Calling Roboflow API ...")
    raw = detector.infer_sync(resized)
    print(f"[+] {len(raw)} detections returned")

    # 4. Parse + annotate
    parser = GameStateParser()
    state = parser.parse(raw, scale_x, scale_y)

    annotated = frame.copy()
    colors = {
        "player": (0, 255, 0),
        "enemy": (0, 0, 255),
        "teammate": (255, 255, 0),
        "power_cube": (0, 255, 255),
        "box": (128, 0, 128),
        "projectile": (0, 128, 255),
        "shot_prodiktion": (0, 80, 200),
        "poison": (0, 128, 0),
        "live_bar": (255, 255, 255),
        "wall": (128, 128, 128),
        "bush": (0, 200, 100),
        "munition": (200, 200, 0),
    }

    for det in raw:
        cls = det.get("class", "")
        cx = int(det["x"] * scale_x)
        cy = int(det["y"] * scale_y)
        w = int(det["width"] * scale_x)
        h = int(det["height"] * scale_y)
        x1, y1 = cx - w // 2, cy - h // 2
        x2, y2 = cx + w // 2, cy + h // 2
        color = colors.get(cls, (200, 200, 200))
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        label = f"{cls} {det.get('confidence', 0):.2f}"
        cv2.putText(annotated, label, (x1, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    cv2.imwrite("calibrate_annotated.jpg", annotated)
    print("[+] Annotated frame saved: calibrate_annotated.jpg")
    print(f"    player={state.player_pos}  enemies={len(state.enemies)}  cubes={len(state.power_cubes)}")


if __name__ == "__main__":
    main()
