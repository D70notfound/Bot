import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bot.geometry import (
    distance, angle_to, point_in_radius,
    move_away_from, weighted_flee_vector, screen_center, quantize_direction,
)


def test_distance_basic():
    assert distance((0, 0), (3, 4)) == pytest.approx(5.0)


def test_distance_same_point():
    assert distance((5, 5), (5, 5)) == 0.0


def test_angle_to_right():
    assert angle_to((0, 0), (1, 0)) == pytest.approx(0.0)


def test_angle_to_up():
    # target above origin means dy < 0, so angle = 90
    assert angle_to((0, 0), (0, -1)) == pytest.approx(90.0)


def test_angle_to_down():
    assert angle_to((0, 0), (0, 1)) == pytest.approx(270.0)


def test_angle_to_left():
    assert angle_to((0, 0), (-1, 0)) == pytest.approx(180.0)


def test_point_in_radius_inside():
    assert point_in_radius((1, 1), (0, 0), 2.0) is True


def test_point_in_radius_outside():
    assert point_in_radius((3, 0), (0, 0), 2.0) is False


def test_move_away_from():
    result = move_away_from((0, 0), (-10, 0), 5.0)
    assert result[0] == pytest.approx(5.0)
    assert result[1] == pytest.approx(0.0)


def test_weighted_flee_vector_single():
    # Threat directly to the left; flee vector should point right
    vx, vy = weighted_flee_vector((0, 0), [(-1, 0)], [1.0])
    assert vx > 0
    assert abs(vy) < 1e-9


def test_weighted_flee_vector_no_threats():
    vx, vy = weighted_flee_vector((0, 0), [], [])
    assert (vx, vy) == (0.0, -1.0)


def test_screen_center():
    region = {"left": 10, "top": 20, "width": 100, "height": 80}
    assert screen_center(region) == (60.0, 60.0)


def test_quantize_direction_east():
    assert quantize_direction(0) == (1, 0)


def test_quantize_direction_north():
    assert quantize_direction(90) == (0, -1)


def test_quantize_direction_west():
    assert quantize_direction(180) == (-1, 0)


def test_quantize_direction_south():
    assert quantize_direction(270) == (0, 1)


def test_quantize_direction_northeast():
    assert quantize_direction(45) == (1, -1)

