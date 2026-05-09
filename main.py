#!/usr/bin/env python3
"""
Brawl Stars Showdown Bot — main entry point.

Usage:
    python main.py [--config config.json]
"""
import argparse
import asyncio
import json
import queue
import signal
import sys
import time
from threading import Thread

from bot.capture import ScreenCapture, WindowNotFoundError
from bot.detection import RoboflowDetector
from bot.game_state import GameStateParser
from bot.input_controller import InputController
from bot.logger import BotLogger
from bot.strategy import ShowdownStrategy


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def detector_worker(
    detector: RoboflowDetector,
    q_in: queue.Queue,
    q_out: queue.Queue,
) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        while True:
            item = q_in.get()
            if item is None:
                break
            resized, sx, sy, fid, t0 = item
            raw = loop.run_until_complete(detector.infer_async(resized))
            infer_ms = (time.perf_counter() - t0) * 1000.0
            # Drop any stale result still sitting in q_out so the main loop
            # always sees the freshest detections.
            try:
                q_out.get_nowait()
            except queue.Empty:
                pass
            try:
                q_out.put_nowait((raw, sx, sy, fid, infer_ms))
            except queue.Full:
                pass
    finally:
        loop.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Brawl Stars bot")
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args()

    config = load_config(args.config)

    if not config["roboflow"]["api_key"]:
        print(
            "[!] roboflow.api_key is empty in config.json\n"
            "    Fill in your Roboflow API key before running the bot."
        )
        sys.exit(1)

    capture = ScreenCapture(config)
    detector = RoboflowDetector(config)
    game_parser = GameStateParser()
    strategy = ShowdownStrategy(config)
    controller = InputController(config)
    logger = BotLogger(config)

    print("[*] Locating emulator window ...")
    try:
        region = capture.find_window()
        print(f"[+] Window: {region}")
    except WindowNotFoundError as e:
        print(f"[!] {e}")
        sys.exit(1)

    strategy.set_screen_region(region)
    controller.set_region(region)

    q_in: queue.Queue = queue.Queue(maxsize=1)
    q_out: queue.Queue = queue.Queue(maxsize=1)
    worker = Thread(target=detector_worker, args=(detector, q_in, q_out), daemon=True)
    worker.start()

    fps_target = max(1, int(config["emulator"].get("fps_target", 10)))
    frame_interval = 1.0 / fps_target
    latest_dets: list = []
    scale_x = scale_y = 1.0
    last_infer_ms = 0.0
    frame_id = 0

    shutdown = {"requested": False}

    def _shutdown(_sig, _frame):
        shutdown["requested"] = True

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("[*] Bot running. Press Ctrl+C to stop.")

    try:
        while not shutdown["requested"]:
            tick_start = time.perf_counter()

            # Capture
            frame = capture.grab_frame()
            resized, sx, sy = capture.resize_for_api(frame)

            # Submit frame to detector (drop if worker still busy)
            try:
                q_in.put_nowait((resized, sx, sy, frame_id, tick_start))
            except queue.Full:
                pass

            # Consume newest detections if any are ready
            try:
                latest_dets, scale_x, scale_y, _, last_infer_ms = q_out.get_nowait()
            except queue.Empty:
                pass

            # Parse → state
            state = game_parser.parse(
                latest_dets, scale_x, scale_y,
                frame_id=frame_id, timestamp=tick_start,
            )

            # Decide
            action = strategy.decide(state)

            # Execute
            if action.stop_moving:
                controller.stop_moving()
            elif action.move_target is not None and state.player_pos is not None:
                controller.move_toward(action.move_target, state.player_pos)

            if action.use_super_at is not None:
                controller.use_super(*action.use_super_at)
            elif action.shoot_target is not None:
                controller.shoot(*action.shoot_target)

            # Log
            loop_ms = (time.perf_counter() - tick_start) * 1000.0
            logger.log_tick(frame_id, state, action, last_infer_ms, loop_ms)
            logger.save_debug_frame(frame, frame_id)

            frame_id += 1

            # Throttle
            elapsed = time.perf_counter() - tick_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    finally:
        print("\n[*] Shutting down ...")
        controller.release_all()
        # Drain and signal worker to exit
        try:
            while True:
                q_in.get_nowait()
        except queue.Empty:
            pass
        try:
            q_in.put_nowait(None)
        except queue.Full:
            pass
        worker.join(timeout=2.0)


if __name__ == "__main__":
    main()
