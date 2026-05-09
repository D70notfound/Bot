import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bot.detection import RoboflowDetector


def make_detector(conf=0.40, overlap=0.30):
    return RoboflowDetector({
        "roboflow": {
            "api_key": "k",
            "workspace": "ws",
            "project": "proj",
            "version": 1,
            "confidence_threshold": conf,
            "overlap_threshold": overlap,
        }
    })


def test_api_params_uses_percent():
    d = make_detector(conf=0.40, overlap=0.30)
    p = d._api_params()
    assert p["confidence"] == 40
    assert p["overlap"] == 30
    assert p["api_key"] == "k"


def test_api_params_rounds_correctly():
    d = make_detector(conf=0.555, overlap=0.001)
    p = d._api_params()
    assert p["confidence"] == 56  # rounded
    assert p["overlap"] == 0


def test_parse_response_filters_low_confidence():
    d = make_detector(conf=0.50)
    raw = {
        "predictions": [
            {"class": "enemy", "confidence": 0.80, "x": 10, "y": 20, "width": 5, "height": 5},
            {"class": "enemy", "confidence": 0.30, "x": 11, "y": 21, "width": 5, "height": 5},
        ]
    }
    out = d._parse_response(raw)
    assert len(out) == 1
    assert out[0]["confidence"] == 0.80


def test_parse_response_handles_empty():
    d = make_detector()
    assert d._parse_response({}) == []
    assert d._parse_response({"predictions": []}) == []
