import re
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import fitz  # PyMuPDF
import cv2
import numpy as np


# Devanagari to ASCII digits mapping
DEVANAGARI_DIGITS = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}

# Devanagari Unicode Range
DEVANAGARI_RANGE_REGEX = re.compile(r'[\u0900-\u097F]')


def has_devanagari_script(text: str) -> bool:
    """Checks if string contains Devanagari characters."""
    return bool(DEVANAGARI_RANGE_REGEX.search(text))


def devanagari_to_ascii(text: str) -> str:
    """Converts Devanagari digits (०-९) to ASCII digits (0-9)."""
    for dev, asc in DEVANAGARI_DIGITS.items():
        text = text.replace(dev, asc)
    return text


class MultilingualOCRAdapter:
    """
    Multilingual & Hindi OCR / Text Extraction Adapter.
    Processes bilingual and Hindi documents (Land Deeds, Fire NOCs, Faculty Lists)
    with Devanagari script detection, numeral translation, and confidence scoring.
    """

    # Lexicon for Hindi & Bilingual regulatory fields
    LAND_KEYWORDS = [
        "क्षेत्रफल", "रकबा", "एकड़", "खसरा", "भूमि माप", "कुल क्षेत्रफल",
        "पंजीकृत क्षेत्रफल", "भूमि विलेख", "खतौनी", "हेक्टेयर"
    ]
    FIRE_NOC_KEYWORDS = [
        "अग्नि सुरक्षा", "अनापत्ति", "अग्नि शमन", "प्रमाण पत्र संख्या", "वैधता",
        "समाप्ति तिथि", "जारी तिथि", "अग्नि निवारण"
    ]
    FACULTY_KEYWORDS = [
        "संकाय", "प्राध्यापक", "सह प्राध्यापक", "सहायक प्राध्यापक", "कुल संकाय",
        "स्वीकृत छात्र", "प्रवेश क्षमता"
    ]

    @classmethod
    def detect_language(cls, text: str) -> str:
        """Determines if text is Hindi, English, or Bilingual."""
        has_dev = has_devanagari_script(text)
        has_lat = bool(re.search(r'[A-Za-z]', text))
        if has_dev and has_lat:
            return "bilingual"
        elif has_dev:
            return "hi"
        return "en"

    @classmethod
    def preprocess_image_for_ocr(cls, img_bytes: bytes) -> np.ndarray:
        """
        Preprocesses an image byte buffer using OpenCV for enhanced OCR text clarity:
        grayscale conversion, Otsu binarization, and morphological filtering.
        """
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Otsu thresholding
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    @classmethod
    def extract_land_deed_data(cls, text: str) -> Dict[str, Any]:
        """
        Extracts land acreage from Hindi or bilingual land documents.
        Supports Devanagari numerals (४.५० एकड़) and Roman numerals (4.50 एकड़).
        """
        normalized_text = devanagari_to_ascii(text)
        is_dev = has_devanagari_script(text)
        
        result = {
            "registered_acres": None,
            "survey_numbers": None,
            "raw_snippet": None,
            "language": cls.detect_language(text),
            "confidence": 0.0,
            "matched_keyword": None,
        }

        # 1. Look for Hindi land measure patterns
        # e.g.: कुल रकबा: 4.50 एकड़, कुल क्षेत्रफल: 5.0 एकड़, भूमि माप: 3.25 एकड़
        patterns = [
            r"(?:कुल\s*रकबा|रकबा|कुल\s*क्षेत्रफल|क्षेत्रफल|भूमि\s*माप|पंजीकृत\s*क्षेत्रफल)\s*[:=\-]?\s*([\d\.]+)\s*(?:एकड़|acres?|हेक्टेयर|hectares?)",
            r"([\d\.]+)\s*(?:एकड़|हेक्टेयर)",
            r"(?:Total Registered Land Measure|Land Measure|Total Area|Registered Area):\s*([\d\.]+)\s*Acres?",
        ]

        for pat in patterns:
            match = re.search(pat, normalized_text, re.IGNORECASE)
            if match:
                val = float(match.group(1))
                # If unit is hectare, convert to acres (1 hectare ≈ 2.47105 acres)
                matched_span = match.group(0)
                if "हेक्टेयर" in matched_span or "hectare" in matched_span.lower():
                    val = round(val * 2.47105, 2)

                result["registered_acres"] = val
                result["raw_snippet"] = matched_span
                result["matched_keyword"] = "land_measure_hindi" if is_dev else "land_measure_en"
                # Confidence calculation based on keyword presence
                kw_count = sum(1 for kw in cls.LAND_KEYWORDS if kw in text)
                result["confidence"] = min(0.95, 0.70 + (0.05 * kw_count)) if is_dev else 0.90
                break

        # 2. Extract Khasra / Survey Number if available
        # e.g.: खसरा संख्या: 124/1, खसरा नं. 45
        m_khasra = re.search(r"(?:खसरा\s*(?:संख्या|नं\.?|क्र\.?)|Survey\s*No\.?)\s*[:=\-]?\s*([0-9\/\-,]+)", normalized_text, re.IGNORECASE)
        if m_khasra:
            result["survey_numbers"] = m_khasra.group(1).strip()

        return result

    @classmethod
    def extract_fire_noc_data(cls, text: str) -> Dict[str, Any]:
        """
        Extracts fire certificate ID, issue date, and expiry date from Hindi/bilingual NOCs.
        """
        normalized_text = devanagari_to_ascii(text)
        is_dev = has_devanagari_script(text)

        result = {
            "certificate_id": None,
            "issue_date": None,
            "expiry_date": None,
            "language": cls.detect_language(text),
            "confidence": 0.0,
            "raw_snippet": None,
        }

        # 1. Certificate ID patterns
        # e.g.: प्रमाण पत्र संख्या: NOC/2024/789 or संदर्भ सं: FS-2024-99
        m_cert = re.search(r"(?:प्रमाण\s*पत्र\s*संख्या|अनापत्ति\s*संख्या|संदर्भ\s*संख्या|Certificate\s*/\s*NOC\s*Reference):\s*([^\n\r]+)", normalized_text, re.IGNORECASE)
        if m_cert:
            result["certificate_id"] = m_cert.group(1).strip()

        # 2. Issue Date patterns
        m_iss = re.search(r"(?:जारी\s*करने\s*की\s*तिथि|जारी\s*तिथि|निरीक्षण\s*तिथि|Date\s*of\s*Issuance|Issue\s*Date):\s*([0-9\-/]+)", normalized_text, re.IGNORECASE)
        if m_iss:
            result["issue_date"] = m_iss.group(1).strip()

        # 3. Expiry Date patterns
        # e.g.: वैधता तिथि: 15-05-2025 or समाप्ति तिथि: 2025-12-31 or वैध अवधि: 31/03/2026
        m_exp = re.search(r"(?:वैधता\s*तिथि|समाप्ति\s*तिथि|अंतिम\s*तिथि|To\s*Expiry\s*Date|Expiry\s*Date|Valid\s*Until):\s*[\r\n\s]*([0-9\-/]+)", normalized_text, re.IGNORECASE)
        if m_exp:
            raw_exp = m_exp.group(1).strip()
            for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
                try:
                    result["expiry_date"] = datetime.strptime(raw_exp, fmt).date()
                    break
                except ValueError:
                    pass

        # Calculate confidence
        if result["certificate_id"] and result["expiry_date"]:
            kw_count = sum(1 for kw in cls.FIRE_NOC_KEYWORDS if kw in text)
            result["confidence"] = min(0.95, 0.75 + (0.05 * kw_count)) if is_dev else 0.90
        elif result["certificate_id"] or result["expiry_date"]:
            result["confidence"] = 0.65
        else:
            result["confidence"] = 0.20 if is_dev else 0.0

        return result

    @classmethod
    def extract_faculty_data(cls, text: str) -> Dict[str, Any]:
        """
        Extracts faculty tier counts and approved student intake from Hindi/bilingual faculty rosters.
        """
        normalized_text = devanagari_to_ascii(text)
        is_dev = has_devanagari_script(text)

        result = {
            "professors": None,
            "assoc_professors": None,
            "asst_professors": None,
            "total_students": None,
            "total_faculty": None,
            "language": cls.detect_language(text),
            "confidence": 0.0,
        }

        # Match Hindi/Bilingual faculty tiers
        # प्राध्यापक / Professors: 3
        # सह प्राध्यापक / Associate Professors: 6
        # सहायक प्राध्यापक / Assistant Professors: 18
        m_prof = re.search(r"(?:प्राध्यापक|Professors?):\s*(\d+)", normalized_text, re.IGNORECASE)
        m_assoc = re.search(r"(?:सह\s*प्राध्यापक|Associate\s*Professors?):\s*(\d+)", normalized_text, re.IGNORECASE)
        m_asst = re.search(r"(?:सहायक\s*प्राध्यापक|Assistant\s*Professors?):\s*(\d+)", normalized_text, re.IGNORECASE)
        m_intake = re.search(r"(?:स्वीकृत\s*छात्र\s*संख्या|छात्र\s*प्रवेश\s*क्षमता|Approved\s*Student\s*Intake|Total\s*Intake):\s*(\d+)", normalized_text, re.IGNORECASE)

        if m_prof and m_assoc and m_asst:
            p = int(m_prof.group(1))
            ap = int(m_assoc.group(1))
            ast = int(m_asst.group(1))
            result["professors"] = p
            result["assoc_professors"] = ap
            result["asst_professors"] = ast
            result["total_faculty"] = p + ap + ast
            if m_intake:
                result["total_students"] = int(m_intake.group(1))
            
            kw_count = sum(1 for kw in cls.FACULTY_KEYWORDS if kw in text)
            result["confidence"] = min(0.95, 0.80 + (0.05 * kw_count)) if is_dev else 0.95
        
        return result
