import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from app.ingestion.normalizer import PDFCoordinateNormalizer
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
