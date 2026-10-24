import pytest
from app.ingestion.normalizer import PDFCoordinateNormalizer


def test_normalizer_upright():
    # Standard A4 upright 595 x 842 pt
    cropbox = (0.0, 0.0, 595.0, 842.0)
    rect = (100.0, 200.0, 200.0, 250.0)
    bbox = PDFCoordinateNormalizer.normalize_rect(rect, cropbox, rotation=0)

    assert bbox.x == round(100.0 / 595.0, 4)
    assert bbox.y == round(200.0 / 842.0, 4)
    assert bbox.width == round(100.0 / 595.0, 4)
    assert bbox.height == round(50.0 / 842.0, 4)


def test_normalizer_rotated_90():
    # Rotated 90 degrees clockwise
    cropbox = (0.0, 0.0, 595.0, 842.0)
    rect = (100.0, 200.0, 200.0, 250.0)
    bbox = PDFCoordinateNormalizer.normalize_rect(rect, cropbox, rotation=90)

    # In 90 deg clockwise, width and height swap: page_w=842, page_h=595
    assert 0.0 <= bbox.x <= 1.0
    assert 0.0 <= bbox.y <= 1.0
    assert bbox.width > 0
    assert bbox.height > 0


def test_normalizer_cropbox_offset():
    # Non-zero cropbox origin (e.g. margin cropped at (50, 50))
    cropbox = (50.0, 50.0, 550.0, 750.0)
    rect = (50.0, 50.0, 150.0, 120.0)
    bbox = PDFCoordinateNormalizer.normalize_rect(rect, cropbox, rotation=0)

    assert bbox.x == 0.0
    assert bbox.y == 0.0
    assert bbox.width == round(100.0 / 500.0, 4)
    assert bbox.height == round(70.0 / 700.0, 4)
