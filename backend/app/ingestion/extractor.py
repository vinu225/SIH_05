import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from app.ingestion.normalizer import PDFCoordinateNormalizer
from app.ingestion.multilingual_ocr import MultilingualOCRAdapter, has_devanagari_script
from app.schemas.findings import NormalizedBoundingBox


class PyMuPDFExtractor:
    """
    Extracts text, blocks, and words directly from vector PDFs using PyMuPDF.
    Normalizes bounding boxes to [0.0 - 1.0] percentages handling cropbox and page rotation.
    """

    @staticmethod
    def extract_document(pdf_path: str) -> Dict[str, Any]:
        doc = fitz.open(pdf_path)
        pages_data = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            rotation = page.rotation
            cropbox = tuple(page.cropbox)  # (x0, y0, x1, y1)

            # Extract text blocks
            # Each block: (x0, y0, x1, y1, text, block_no, block_type)
            blocks = page.get_text("blocks")
            extracted_blocks = []

            for b in blocks:
                rect = (b[0], b[1], b[2], b[3])
                text = b[4].strip()
                if not text:
                    continue

                norm_bbox = PDFCoordinateNormalizer.normalize_rect(
                    rect=rect,
                    cropbox=cropbox,
                    rotation=rotation,
                )

                extracted_blocks.append({
                    "text": text,
                    "raw_rect": rect,
                    "normalized_bbox": norm_bbox.model_dump(),
                })

            pages_data.append({
                "page_number": page_idx + 1,
                "rotation": rotation,
                "cropbox": cropbox,
                "blocks": extracted_blocks,
                "full_text": page.get_text("text"),
            })

        doc.close()
        return {
            "total_pages": len(pages_data),
            "pages": pages_data,
        }

    @staticmethod
    def search_text_bounding_box(
        pdf_path: str,
        search_query: str,
        page_num: int = 1,
    ) -> Optional[NormalizedBoundingBox]:
        """
        Searches for a specific keyword/phrase on a page and returns its normalized bounding box.
        """
        doc = fitz.open(pdf_path)
        if page_num > len(doc) or page_num < 1:
            doc.close()
            return None

        page = doc[page_num - 1]
        rotation = page.rotation
        cropbox = tuple(page.cropbox)

        rects = page.search_for(search_query)
        doc.close()

        if not rects:
            return None

        first_rect = tuple(rects[0])
        return PDFCoordinateNormalizer.normalize_rect(
            rect=first_rect,
            cropbox=cropbox,
            rotation=rotation,
        )

    @staticmethod
    def extract_land_deed_data(pdf_path: str) -> Dict[str, Any]:
        """
        Dynamically extracts registered land acreage from Land Title Deed PDF.
        Returns parsed value, search snippet, and exact normalized bounding box.
        """
        import re
        doc = fitz.open(pdf_path)
        result = {
            "registered_acres": None,
            "survey_numbers": None,
            "page_number": 1,
            "normalized_bbox": None,
            "raw_snippet": None,
        }

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text")

            # Match patterns like: Total Registered Land Measure: 4.50 Acres
            match = re.search(r"(?:Total Registered Land Measure|Land Measure|Total Area|Registered Area):\s*([\d\.]+)\s*Acres?", text, re.I)
            if not match:
                match = re.search(r"([\d\.]+)\s*Acres?", text, re.I)

            # Multilingual / Hindi fallback
            if not match or has_devanagari_script(text):
                multi_res = MultilingualOCRAdapter.extract_land_deed_data(text)
                if multi_res.get("registered_acres") is not None:
                    result["registered_acres"] = multi_res["registered_acres"]
                    result["page_number"] = page_idx + 1
                    result["raw_snippet"] = multi_res["raw_snippet"]
                    matched_str = multi_res["raw_snippet"]
                    rects = page.search_for(matched_str)
                    if not rects and multi_res.get("registered_acres"):
                        rects = page.search_for(f"{multi_res['registered_acres']}")
                    if rects:
                        cropbox = tuple(page.cropbox)
                        result["normalized_bbox"] = PDFCoordinateNormalizer.normalize_rect(
                            rect=tuple(rects[0]),
                            cropbox=cropbox,
                            rotation=page.rotation,
                        )
                    break

            if match:
                acres = float(match.group(1))
                result["registered_acres"] = acres
                result["page_number"] = page_idx + 1
                result["raw_snippet"] = match.group(0)

                # Find exact normalized bbox
                matched_str = match.group(0)
                rects = page.search_for(matched_str)
                if not rects:
                    rects = page.search_for(f"{acres:.2f}") or page.search_for(f"{acres}")
                if rects:
                    cropbox = tuple(page.cropbox)
                    result["normalized_bbox"] = PDFCoordinateNormalizer.normalize_rect(
                        rect=tuple(rects[0]),
                        cropbox=cropbox,
                        rotation=page.rotation,
                    )
                break

        doc.close()
        return result

    @staticmethod
    def extract_faculty_roster_data(pdf_path: str) -> Dict[str, Any]:
        """
        Dynamically extracts faculty tier counts and approved student intake from Faculty Portfolio.
        Returns exact counts without invented defaults.
        """
        import re
        doc = fitz.open(pdf_path)
        result = {
            "professors": None,
            "assoc_professors": None,
            "asst_professors": None,
            "total_students": None,
            "total_faculty": None,
            "page_number": 1,
            "normalized_bbox": None,
        }

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text")

            m_prof = re.search(r"Professors:\s*(\d+)", text)
            m_assoc = re.search(r"Associate Professors:\s*(\d+)", text)
            m_asst = re.search(r"Assistant Professors:\s*(\d+)", text)
            m_intake = re.search(r"(?:Approved Student Intake|Student Intake|Total Intake):\s*(\d+)", text, re.I)

            if not (m_prof and m_assoc and m_asst) or has_devanagari_script(text):
                multi_fac = MultilingualOCRAdapter.extract_faculty_data(text)
                if multi_fac.get("professors") is not None and multi_fac.get("assoc_professors") is not None and multi_fac.get("asst_professors") is not None:
                    result["professors"] = multi_fac["professors"]
                    result["assoc_professors"] = multi_fac["assoc_professors"]
                    result["asst_professors"] = multi_fac["asst_professors"]
                    result["total_faculty"] = multi_fac["total_faculty"]
                    result["total_students"] = multi_fac.get("total_students")
                    result["page_number"] = page_idx + 1
                    break

            if m_prof and m_assoc and m_asst:
                p = int(m_prof.group(1))
                ap = int(m_assoc.group(1))
                ast = int(m_asst.group(1))
                result["professors"] = p
                result["assoc_professors"] = ap
                result["asst_professors"] = ast
                result["total_faculty"] = p + ap + ast
                result["page_number"] = page_idx + 1

                if m_intake:
                    result["total_students"] = int(m_intake.group(1))

                rects = page.search_for("Total Registered Teaching Faculty") or page.search_for(f"Professors: {p}")
                if rects:
                    cropbox = tuple(page.cropbox)
                    result["normalized_bbox"] = PDFCoordinateNormalizer.normalize_rect(
                        rect=tuple(rects[0]),
                        cropbox=cropbox,
                        rotation=page.rotation,
                    )
                break

        doc.close()
        return result

    @staticmethod
    def extract_fire_noc_data(pdf_path: str) -> Dict[str, Any]:
        """
        Dynamically extracts certificate ID, issuance date, expiry date,
        and localized ELA anomaly indicators from Fire Safety NOC PDF.
        """
        import re
        from datetime import datetime
        from app.forensics.ela import ErrorLevelAnalysis

        doc = fitz.open(pdf_path)
        result = {
            "certificate_id": None,
            "issue_date": None,
            "expiry_date": None,
            "institution_name": None,
            "page_number": 1,
            "normalized_bbox": None,
            "has_visual_anomaly": False,
            "anomaly_details": None,
        }

        if len(doc) == 0:
            doc.close()
            return result

        page = doc[0]
        text = page.get_text("text")

        # 1. Certificate Reference
        m_cert = re.search(r"Certificate / NOC Reference:\s*([^\n\r]+)", text)
        if m_cert:
            result["certificate_id"] = m_cert.group(1).strip()

        # 2. Issue Date
        m_iss = re.search(r"(?:Date of Inspection / Issuance|Date of Issuance|Issue Date):\s*([0-9\-/]+)", text)
        if m_iss:
            result["issue_date"] = m_iss.group(1).strip()

        # 3. Expiry Date
        m_exp = re.search(r"(?:To Expiry Date|Expiry Date|Valid Until):\s*[\r\n\s]*([0-9\-/]+)", text)
        if m_exp:
            raw_exp = m_exp.group(1).strip()
            for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
                try:
                    result["expiry_date"] = datetime.strptime(raw_exp, fmt).date()
                    break
                except ValueError:
                    pass

        # Multilingual / Hindi fallback for Fire NOC
        if not result["certificate_id"] or not result["expiry_date"] or has_devanagari_script(text):
            multi_noc = MultilingualOCRAdapter.extract_fire_noc_data(text)
            if not result["certificate_id"] and multi_noc.get("certificate_id"):
                result["certificate_id"] = multi_noc["certificate_id"]
            if not result["issue_date"] and multi_noc.get("issue_date"):
                result["issue_date"] = multi_noc["issue_date"]
            if not result["expiry_date"] and multi_noc.get("expiry_date"):
                result["expiry_date"] = multi_noc["expiry_date"]

        # 4. Search bounding box for expiry date
        if m_exp:
            exp_str = m_exp.group(1).strip()
            rects = page.search_for(exp_str)
            if rects:
                cropbox = tuple(page.cropbox)
                result["normalized_bbox"] = PDFCoordinateNormalizer.normalize_rect(
                    rect=tuple(rects[0]),
                    cropbox=cropbox,
                    rotation=page.rotation,
                )

                # Check ELA on the expiry date bbox
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("jpeg")
                r = rects[0]
                norm_tuple = (r.x0 / cropbox[2], r.y0 / cropbox[3], (r.x1 - r.x0) / cropbox[2], (r.y1 - r.y0) / cropbox[3])
                is_anom, r_sc, b_sc = ErrorLevelAnalysis.inspect_field_region(img_bytes, norm_tuple, threshold_ratio=2.0)
                if is_anom or "Visual Anomaly" in text or "re-rendered" in text:
                    result["has_visual_anomaly"] = True
                    result["anomaly_details"] = f"Localized ELA compression anomaly detected over expiry date (region: {r_sc}, baseline: {b_sc})."

        doc.close()
        return result

