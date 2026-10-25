import pytest
from datetime import date
from pathlib import Path
import tempfile
import sys
import fitz

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.ingestion.multilingual_ocr import (
    MultilingualOCRAdapter,
    has_devanagari_script,
    devanagari_to_ascii,
)
from app.ingestion.extractor import PyMuPDFExtractor


@pytest.mark.unit
def test_devanagari_detection_and_numeral_translation():
    """Verify script identification and numeral mapping."""
    hindi_text = "भूमि विलेख एवं खसरा खतौनी"
    ascii_text = "Land Title Deed and Revenue Record"
    assert has_devanagari_script(hindi_text) is True
    assert has_devanagari_script(ascii_text) is False

    devanagari_num = "क्षेत्रफल: ४.५० एकड़, खसरा: १२३/४५"
    converted = devanagari_to_ascii(devanagari_num)
    assert "4.50" in converted
    assert "123/45" in converted


@pytest.mark.unit
def test_multilingual_land_deed_extraction_hindi_numerals():
    """Verify extraction of acreage specified in Devanagari numerals."""
    doc_text = """
    उत्तर प्रदेश राजस्व परिषद
    भूमि अभिलेख विवरण
    खसरा संख्या: 412/1
    कुल रकबा: ४.५० एकड़
    पंजीकृत स्वामी: श्री सरस्वती शिक्षण संस्थान
    """
    res = MultilingualOCRAdapter.extract_land_deed_data(doc_text)
    assert res["registered_acres"] == 4.5
    assert res["language"] == "hi"
    assert res["confidence"] >= 0.75
    assert res["survey_numbers"] == "412/1"


@pytest.mark.unit
def test_multilingual_land_deed_extraction_hectares():
    """Verify conversion of land recorded in hectares to acres."""
    doc_text = """
    मध्य प्रदेश शासन - राजस्व विभाग
    प्रमाणित भूमि विवरण
    कुल क्षेत्रफल: 2.00 हेक्टेयर
    """
    res = MultilingualOCRAdapter.extract_land_deed_data(doc_text)
    # 2.0 hectares * 2.47105 ≈ 4.94 acres
    assert res["registered_acres"] == pytest.approx(4.94, 0.05)
    assert res["confidence"] >= 0.70


@pytest.mark.unit
def test_multilingual_fire_noc_extraction():
    """Verify extraction of fire safety certificate ID and expiry date from Hindi NOC."""
    doc_text = """
    अग्नि शमन एवं आपातकालीन सेवाएं
    अनापत्ति प्रमाण पत्र (Fire Safety NOC)
    प्रमाण पत्र संख्या: NOC-UP-FIRE-2024-8899
    जारी तिथि: 10-01-2024
    वैधता तिथि: 09-01-2027
    यह प्रमाणित किया जाता है कि संस्थान परिसर का निरीक्षण कर अग्नि सुरक्षा मानक पूर्ण पाए गए।
    """
    res = MultilingualOCRAdapter.extract_fire_noc_data(doc_text)
    assert res["certificate_id"] == "NOC-UP-FIRE-2024-8899"
    assert res["expiry_date"] == date(2027, 1, 9)
    assert res["language"] == "bilingual"
    assert res["confidence"] >= 0.85


@pytest.mark.unit
def test_multilingual_faculty_roster_extraction():
    """Verify extraction of faculty cadres and intake from Hindi roster."""
    doc_text = """
    संकाय विवरण एवं छात्र प्रवेश क्षमता
    स्वीकृत छात्र संख्या: 360
    प्राध्यापक: 3
    सह प्राध्यापक: 6
    सहायक प्राध्यापक: 9
    """
    res = MultilingualOCRAdapter.extract_faculty_data(doc_text)
    assert res["professors"] == 3
    assert res["assoc_professors"] == 6
    assert res["asst_professors"] == 9
    assert res["total_faculty"] == 18
    assert res["total_students"] == 360
    assert res["confidence"] >= 0.85


@pytest.mark.unit
def test_multilingual_confidence_unparseable_text():
    """Verify unparseable text returns low confidence to route to manual review."""
    unparseable_text = "कुछ अस्पष्ट पाठ जो किसी नियामक प्रारूप से मेल नहीं खाता"
    res = MultilingualOCRAdapter.extract_fire_noc_data(unparseable_text)
    assert res["certificate_id"] is None
    assert res["expiry_date"] is None
    assert res["confidence"] < 0.50


@pytest.mark.integration
def test_pymupdf_extractor_with_bilingual_pdf():
    """Verify PyMuPDFExtractor dynamically extracts land acreage from a generated bilingual PDF."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Create a single-page PDF with Hindi land content
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)
        # Using a standard font to render text
        page.insert_text(
            (50, 100),
            "State Revenue Department / राज्य राजस्व विभाग\nLand Measure / कुल रकबा: 5.75 Acres / एकड़",
            fontsize=12,
        )
        doc.save(tmp_path)
        doc.close()

        extracted = PyMuPDFExtractor.extract_land_deed_data(tmp_path)
        assert extracted["registered_acres"] == 5.75
        assert extracted["page_number"] == 1
    finally:
        Path(tmp_path).unlink(missing_ok=True)
