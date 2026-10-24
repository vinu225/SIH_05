from typing import Tuple, Dict, Any
from app.schemas.findings import NormalizedBoundingBox


class PDFCoordinateNormalizer:
    """
    Normalizes PyMuPDF / PDF bounding rectangles into resolution-independent
    normalized percentages [0.0 - 1.0] with top-left origin, explicitly
    accounting for Page Rotation (0, 90, 180, 270 deg) and CropBox origin offsets
    in accordance with PDF.js rendering viewport logic.
    """

    @staticmethod
    def normalize_rect(
        rect: Tuple[float, float, float, float],  # (x0, y0, x1, y1) in PDF points
        cropbox: Tuple[float, float, float, float],  # (crop_x0, crop_y0, crop_x1, crop_y1)
        rotation: int = 0,  # 0, 90, 180, 270 degrees
    ) -> NormalizedBoundingBox:
        x0, y0, x1, y1 = rect
        cx0, cy0, cx1, cy1 = cropbox

        # Step 1: Adjust for CropBox origin offset
        x0 -= cx0
        x1 -= cx0
        y0 -= cy0
        y1 -= cy0

        crop_w = max(cx1 - cx0, 1.0)
        crop_h = max(cy1 - cy0, 1.0)

        # Step 2: Handle Page Rotation matching PDF.js viewport transformation
        # PDF.js renders top-left origin relative to the visible page orientation
        rot = rotation % 360
        if rot == 0:
            final_x0 = x0
            final_y0 = y0
            final_x1 = x1
            final_y1 = y1
            page_w, page_h = crop_w, crop_h

        elif rot == 90:
            # 90 deg clockwise rotation in PDF.js:
            # (x, y) maps to (y, crop_w - x)
            final_x0 = y0
            final_y0 = crop_w - x1
            final_x1 = y1
            final_y1 = crop_w - x0
            page_w, page_h = crop_h, crop_w

        elif rot == 180:
            # 180 deg rotation:
            final_x0 = crop_w - x1
            final_y0 = crop_h - y1
            final_x1 = crop_w - x0
            final_y1 = crop_h - y0
            page_w, page_h = crop_w, crop_h

        elif rot == 270:
            # 270 deg clockwise (90 counter-clockwise):
            final_x0 = crop_h - y1
            final_y0 = x0
            final_x1 = crop_h - y0
            final_y1 = x1
            page_w, page_h = crop_h, crop_w

        else:
            final_x0, final_y0, final_x1, final_y1 = x0, y0, x1, y1
            page_w, page_h = crop_w, crop_h

        # Step 3: Compute normalized fractions [0.0 - 1.0] clamped to boundaries
        norm_x = max(0.0, min(1.0, final_x0 / page_w))
        norm_y = max(0.0, min(1.0, final_y0 / page_h))
        norm_w = max(0.0, min(1.0 - norm_x, (final_x1 - final_x0) / page_w))
        norm_h = max(0.0, min(1.0 - norm_y, (final_y1 - final_y0) / page_h))

        return NormalizedBoundingBox(
            x=round(norm_x, 4),
            y=round(norm_y, 4),
            width=round(norm_w, 4),
            height=round(norm_h, 4),
        )
