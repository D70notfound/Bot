import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bot.game_state import GameStateParser, GameState

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_detections.json")


@pytest.fixture
def raw_detections():
    with open(FIXTURE) as f:
        return json.load(f)["predictions"]


@pytest.fixture
def state(raw_detections):
    parser = GameStateParser()
    return parser.parse(raw_detections, scale_x=1.0, scale_y=1.0, frame_id=1, timestamp=0.0)


def test_player_detected(state):
    assert state.player is not None
    assert state.player.cls == "player"


def test_player_position(state):
    pos = state.player_pos
    assert pos == (320.0, 240.0)


def test_enemy_count(state):
    assert len(state.enemies) == 2


def test_power_cube_count(state):
    assert len(state.power_cubes) == 2


def test_box_count(state):
    assert len(state.boxes) == 1


def test_projectile_count(state):
    assert len(state.projectiles) == 1


def test_shot_prediction_count(state):
    assert len(state.shot_predictions) == 1


def test_poison_count(state):
    assert len(state.poison_zones) == 1


def test_teammate_count(state):
    assert len(state.teammates) == 1


def test_nearest_enemy(state):
    # Enemy at (500, 200) is dist ~180, enemy at (100, 350) is dist ~270
    # So nearest should be (500, 200)
    enemy = state.nearest_enemy
    assert enemy is not None
    assert enemy.bbox.cx == pytest.approx(500.0)


def test_nearest_power_cube(state):
    # Cube at (380, 260) is closer to player (320, 240) than (200, 180)
    cube = state.nearest_power_cube
    assert cube is not None
    assert cube.bbox.cx == pytest.approx(380.0)


def test_incoming_projectiles(state):
    # Projectile at (340, 250) is ~20px from player (320, 240) — within 200px threshold
    assert len(state.incoming_projectiles) >= 1


def test_unknown_class_ignored(raw_detections):
    raw_detections.append({"class": "unknown_thing", "confidence": 0.9,
                            "x": 100, "y": 100, "width": 10, "height": 10})
    parser = GameStateParser()
    state = parser.parse(raw_detections, 1.0, 1.0)
    # Should not raise; just ignore unknown class


def test_scale_applied(raw_detections):
    parser = GameStateParser()
    state = parser.parse(raw_detections, scale_x=2.0, scale_y=2.0)
    assert state.player.bbox.cx == pytest.approx(640.0)
    assert state.player.bbox.cy == pytest.approx(480.0)


def test_no_player_returns_none_pos():
    parser = GameStateParser()
    state = parser.parse([], 1.0, 1.0)
    assert state.player_pos is None
    assert state.nearest_enemy is None
    assert state.nearest_power_cube is None
