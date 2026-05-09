import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bot.input_controller import InputController


def make_controller(movement_keys=None, backend="none"):
    cfg = {
        "input": {
            "backend": backend,
            "movement_keys": movement_keys or {
                "up": "w", "down": "s", "left": "a", "right": "d",
            },
            "shoot_key": "mouse_left",
            "super_key": "f",
        }
    }
    c = InputController(cfg)
    # Force a known backend so we don't actually press keys / move the mouse.
    c._backend = "none"
    c._kb = None
    c._mouse = None
    return c


def test_set_region_offsets_aim_target():
    c = make_controller()
    c.set_region({"left": 100, "top": 50, "width": 800, "height": 600})
    assert c._to_absolute(10, 20) == (110, 70)


def test_set_region_default_is_zero():
    c = make_controller()
    assert c._to_absolute(5, 7) == (5, 7)


def test_movement_keys_from_config_used():
    c = make_controller({"up": "i", "down": "k", "left": "j", "right": "l"})
    assert c._direction_keys[(1, 0)] == ["l"]
    assert c._direction_keys[(0, -1)] == ["i"]
    assert c._direction_keys[(-1, 1)] == ["k", "j"]


def test_move_toward_holds_correct_keys(monkeypatch):
    c = make_controller()
    captured = []

    def fake_set(desired):
        captured.append(set(desired))

    monkeypatch.setattr(c, "_set_held_keys", fake_set)

    # Target to the right of player → angle 0 → east → key "d"
    c.move_toward((100, 0), (0, 0))
    assert captured[-1] == {"d"}

    # Target above player (smaller y) → north → key "w"
    c.move_toward((0, -100), (0, 0))
    assert captured[-1] == {"w"}


def test_stop_moving_releases_held_keys():
    c = make_controller()
    c._held = {"w", "d"}
    released = []
    c._key_up = lambda k: released.append(k)
    c._key_down = lambda k: None
    c.stop_moving()
    assert set(released) == {"w", "d"}
    assert c._held == set()


def test_move_toward_skips_when_player_pos_none():
    c = make_controller()
    c._set_held_keys = lambda d: pytest.fail("should not be called")
    c.move_toward((10, 10), None)
