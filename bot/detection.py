from __future__ import annotations
import io
import time

import numpy as np
import requests

try:
    import aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False


class RoboflowDetector:
    def __init__(self, config: dict):
        rf = config["roboflow"]
        self._api_key = rf["api_key"]
        self._url = (
            f"https://detect.roboflow.com/{rf['workspace']}/{rf['project']}/{rf['version']}"
        )
        self._confidence = rf["confidence_threshold"]
        self._overlap = rf["overlap_threshold"]
        self._timeout = 3.0
        self._session = None  # aiohttp.ClientSession, created lazily

    # ------------------------------------------------------------------
    # Async (used by main loop via detector thread)
    # ------------------------------------------------------------------

    async def infer_async(self, frame: np.ndarray) -> list:
        if not _AIOHTTP_AVAILABLE:
            return self.infer_sync(frame)

        import aiohttp as ah

        jpeg_bytes = self._encode_frame(frame)
        params = {
            "api_key": self._api_key,
            "confidence": self._confidence,
            "overlap": self._overlap,
        }
        try:
            if self._session is None or self._session.closed:
                self._session = ah.ClientSession()
            form = ah.FormData()
            form.add_field("file", jpeg_bytes, filename="frame.jpg",
                           content_type="image/jpeg")
            async with self._session.post(
                self._url, params=params, data=form,
                timeout=ah.ClientTimeout(total=self._timeout)
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return self._parse_response(data)
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Sync (used by calibrate.py and tests)
    # ------------------------------------------------------------------

    def infer_sync(self, frame: np.ndarray) -> list:
        jpeg_bytes = self._encode_frame(frame)
        params = {
            "api_key": self._api_key,
            "confidence": self._confidence,
            "overlap": self._overlap,
        }
        try:
            resp = requests.post(
                self._url,
                params=params,
                files={"file": ("frame.jpg", jpeg_bytes, "image/jpeg")},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return self._parse_response(resp.json())
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _encode_frame(self, frame: np.ndarray) -> bytes:
        import cv2
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            raise RuntimeError("Failed to JPEG-encode frame")
        return buf.tobytes()

    def _parse_response(self, data: dict) -> list:
        predictions = data.get("predictions", [])
        result = []
        for p in predictions:
            if p.get("confidence", 0) < self._confidence:
                continue
            result.append({
                "class": p.get("class", ""),
                "confidence": p.get("confidence", 0.0),
                "x": float(p.get("x", 0)),
                "y": float(p.get("y", 0)),
                "width": float(p.get("width", 0)),
                "height": float(p.get("height", 0)),
            })
        return result
