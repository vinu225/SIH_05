import io
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image, ImageChops, ImageEnhance
import numpy as np


class ErrorLevelAnalysis:
    """
    Algorithmic Error Level Analysis (ELA) for detecting JPEG compression anomalies
    and generating visual inspection heatmaps.
    Operates strictly as an advisory warning signal, not proof of forgery.
    """

    @staticmethod
    def generate_ela_heatmap(
        image_bytes: bytes,
        resave_quality: int = 90,
        scale: float = 15.0,
    ) -> Tuple[bytes, float]:
        """
        Generates an ELA difference image and computes the mean anomaly difference score.
        Returns (ela_jpeg_bytes, anomaly_score_float).
        """
        orig = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Save to memory buffer at standardized JPEG quality
        buffer = io.BytesIO()
        orig.save(buffer, "JPEG", quality=resave_quality)
        buffer.seek(0)
        resaved = Image.open(buffer)

        # Compute absolute difference between original and resaved
        diff = ImageChops.difference(orig, resaved)

        # Scale difference so compression variations become visually prominent
        extrema = diff.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        if max_diff == 0:
            max_diff = 1
        scale_factor = min(255.0 / max_diff, scale)
        enhancer = ImageEnhance.Brightness(diff)
        diff_scaled = enhancer.enhance(scale_factor)

        # Compute numeric anomaly score (mean luminance of difference)
        diff_arr = np.array(diff)
        mean_anomaly = float(np.mean(diff_arr))

        # Export scaled heatmap overlay as JPEG
        out_buf = io.BytesIO()
        diff_scaled.save(out_buf, "JPEG", quality=95)
        return out_buf.getvalue(), round(mean_anomaly, 3)

    @staticmethod
    def inspect_field_region(
        image_bytes: bytes,
        norm_bbox: Tuple[float, float, float, float],  # (x, y, w, h) in 0.0-1.0
        threshold_ratio: float = 2.2,
    ) -> Tuple[bool, float, float]:
        """
        Compares localized ELA variance in the bounding box against the document's baseline.
        Returns (is_anomaly_detected, region_score, baseline_score).
        """
        orig = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = orig.size

        # Resave
        buf = io.BytesIO()
        orig.save(buf, "JPEG", quality=90)
        buf.seek(0)
        resaved = Image.open(buf)
        diff = ImageChops.difference(orig, resaved)
        diff_arr = np.array(diff)

        # Document global baseline mean
        baseline_score = float(np.mean(diff_arr))

        # Crop region
        x, y, bw, bh = norm_bbox
        x0 = int(x * w)
        y0 = int(y * h)
        x1 = min(int((x + bw) * w), w)
        y1 = min(int((y + bh) * h), h)

        if x1 <= x0 or y1 <= y0:
            return False, baseline_score, baseline_score

        region_arr = diff_arr[y0:y1, x0:x1]
        region_score = float(np.mean(region_arr))

        is_anomaly = region_score > (baseline_score * threshold_ratio) and region_score > 3.0
        return is_anomaly, round(region_score, 3), round(baseline_score, 3)
