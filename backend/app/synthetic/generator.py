import json
import os
from pathlib import Path
from datetime import date, timedelta
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import qrcode
import io


class SyntheticDatasetGenerator:
    """
    Generates synthetic Indian technical institution document packages and
    standardized ground_truth.json benchmarks for testing and demonstration.
    """

    def __init__(self, output_base_dir: str):
        self.base_dir = Path(output_base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _generate_qr_image(self, payload: str) -> io.BytesIO:
        qr = qrcode.QRCode(version=1, box_size=4, border=1)
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    def generate_fire_noc_pdf(
        self,
        filepath: Path,
        institution_name: str,
        clearance_no: str,
        issue_date: str,
        expiry_date: str,
        qr_payload: str,
        tampered_year_overlay: bool = False,
    ):
        c = canvas.Canvas(str(filepath), pagesize=A4)
        w, h = A4

        # Header
        c.setFillColor(colors.HexColor("#1e3a8a"))
        c.rect(0, h - 70, w, 70, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(w / 2, h - 35, "DIRECTORATE OF FIRE & EMERGENCY SERVICES")
        c.setFont("Helvetica", 10)
        c.drawCentredString(w / 2, h - 52, "GOVERNMENT OF NATIONAL CAPITAL TERRITORY / STATE EMERGENCY CELL")

        # Document Title
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(w / 2, h - 110, "FIRE SAFETY CLEARANCE CERTIFICATE (NOC)")
        c.setStrokeColor(colors.HexColor("#cbd5e1"))
        c.line(50, h - 120, w - 50, h - 120)

        # Body text
        c.setFont("Helvetica", 10)
        c.drawString(60, h - 150, f"Certificate / NOC Reference: {clearance_no}")
        c.drawString(60, h - 170, f"Date of Inspection / Issuance: {issue_date}")
        c.drawString(60, h - 200, "Certified that the premises of technical institution:")
        c.setFont("Helvetica-Bold", 11)
        c.drawString(60, h - 220, institution_name)
        c.setFont("Helvetica", 10)
        c.drawString(
            60,
            h - 245,
            "has complied with the mandatory fire prevention and safety requirements under applicable State Fire By-Laws.",
        )

        # Validity Clause
        c.setStrokeColor(colors.HexColor("#94a3b8"))
        c.rect(55, h - 320, w - 110, 50, fill=0, stroke=1)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(70, h - 290, "CERTIFICATE VALIDITY PERIOD:")
        c.setFont("Helvetica", 11)
        c.drawString(70, h - 310, f"Valid From: {issue_date}    To Expiry Date: ")

        if tampered_year_overlay:
            # Visually modified date to simulate rasterized alteration
            c.setFont("Helvetica-Bold", 12)
            c.setFillColor(colors.HexColor("#0f172a"))
            c.drawString(320, h - 310, expiry_date)
        else:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(320, h - 310, expiry_date)

        c.setFillColor(colors.black)

        # Official Stamp and Signatures
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(60, h - 420, "Authorized Signatory: Chief Fire Officer")
        c.drawString(60, h - 435, "Directorate of Fire & Emergency Services")

        # Draw QR code
        qr_buf = self._generate_qr_image(qr_payload)
        from reportlab.lib.utils import ImageReader
        qr_img = ImageReader(qr_buf)
        c.drawImage(qr_img, w - 160, h - 450, width=90, height=90)
        c.setFont("Helvetica", 8)
        c.drawCentredString(w - 115, h - 460, "Scan to Verify at Issuer Portal")

        c.save()

    def generate_land_title_deed_pdf(
        self,
        filepath: Path,
        institution_name: str,
        survey_numbers: str,
        registered_acres: float,
    ):
        c = canvas.Canvas(str(filepath), pagesize=A4)
        w, h = A4

        # Stamp Header
        c.setFillColor(colors.HexColor("#7c2d12"))
        c.rect(0, h - 60, w, 60, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(w / 2, h - 35, "GOVERNMENT OF INDIA - NON-JUDICIAL E-STAMP")
        c.setFont("Helvetica", 9)
        c.drawCentredString(w / 2, h - 50, "CERTIFICATE OF CONVEYANCE & TITLE DEED REGISTRATION")

        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(w / 2, h - 100, "REGISTERED INDENTURE OF SALE / SETTLEMENT")

        c.setFont("Helvetica", 10)
        c.drawString(60, h - 140, "This Indenture of Transfer made between Grantor Trust and Purchaser Institution:")
        c.setFont("Helvetica-Bold", 11)
        c.drawString(60, h - 160, institution_name)

        # Schedule of Property (The critical clause)
        c.setStrokeColor(colors.HexColor("#cbd5e1"))
        c.rect(55, h - 280, w - 110, 90, fill=0, stroke=1)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(70, h - 210, "SCHEDULE OF PROPERTY CONVEYED (PARCEL A):")
        c.setFont("Helvetica", 10)
        c.drawString(70, h - 235, f"Revenue Survey Number(s): {survey_numbers}")
        c.drawString(70, h - 255, f"Total Registered Land Measure: {registered_acres:.2f} Acres (Contiguous)")

        c.setFont("Helvetica", 9)
        c.drawString(60, h - 330, "Conforming to local authority master plan & Town Planning FSI/FAR regulations.")
        c.drawString(60, h - 400, "Sub-Registrar Office Seal & Registration Attestation: Confirmed (Volume 42, Page 119)")

        c.save()

    def generate_faculty_portfolio_pdf(
        self,
        filepath: Path,
        institution_name: str,
        professors: int,
        assoc_professors: int,
        asst_professors: int,
        total_students: int,
    ):
        c = canvas.Canvas(str(filepath), pagesize=A4)
        w, h = A4

        c.setFillColor(colors.HexColor("#0f172a"))
        c.rect(0, h - 50, w, 50, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(w / 2, h - 32, "FACULTY PORTFOLIO & APPOINTMENT ROLL")

        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawString(50, h - 80, f"Institution: {institution_name}")
        c.drawString(50, h - 100, f"Academic Session: 2024-2025 | Total Approved Student Intake: {total_students}")

        total_fac = professors + assoc_professors + asst_professors
        c.drawString(50, h - 130, f"Total Registered Teaching Faculty: {total_fac}")
        c.drawString(70, h - 150, f"• Professors: {professors}")
        c.drawString(70, h - 170, f"• Associate Professors: {assoc_professors}")
        c.drawString(70, h - 190, f"• Assistant Professors: {asst_professors}")

        c.save()

    def build_all_scenarios(self):
        scenarios = [
            {
                "id": "INST-01-COMPLIANT",
                "name": "K.J. Somaiya Institute of Engineering & Technology",
                "program": "ENGINEERING_AND_TECHNOLOGY",
                "students": 240,
                "declared_land": 4.5,
                "deed_land": 4.5,
                "prof": 2,
                "assoc_prof": 4,
                "asst_prof": 12,  # 18 fac for 240 -> 1:13.3 (surpasses 1:20)
                "fire_expiry": "15-06-2027",
                "qr_url": "https://nad.digitallocker.gov.in/verify/CERT-2024-9812",
                "tampered_date": False,
                "expected_status": "COMPLIANT",
            },
            {
                "id": "INST-02-DATE-ALTERED",
                "name": "Vidyavardhini Technical Institute of Technology",
                "program": "ENGINEERING_AND_TECHNOLOGY",
                "students": 240,
                "declared_land": 3.0,
                "deed_land": 3.0,
                "prof": 2,
                "assoc_prof": 3,
                "asst_prof": 10,
                "fire_expiry": "15-03-2026",  # Actually expired 2021, visually altered
                "qr_url": "https://mahafireservice.gov.in/portal/verify/FS-2021-0812",
                "tampered_date": True,
                "expected_status": "UNABLE_TO_DETERMINE_ISOLATED_VISUAL_ANOMALY",
            },
            {
                "id": "INST-03-LAND-CADRE-DISCREPANCY",
                "name": "Apex National Institute of Management & Science",
                "program": "ENGINEERING_AND_TECHNOLOGY",
                "students": 300,
                "declared_land": 5.0,  # Declared 5.0 acres
                "deed_land": 2.1,      # Deed documents 2.1 acres -> 2.9 acre variance
                "prof": 0,             # Cadre violation: 0 professors
                "assoc_prof": 2,
                "asst_prof": 14,
                "fire_expiry": "30-12-2026",
                "qr_url": "https://aicte-india.org/eoa/verify/EOA-2024-1182",
                "tampered_date": False,
                "expected_status": "DISCREPANCY_FOUND",
            },
            {
                "id": "INST-04-UNTRUSTED-QR-GPS",
                "name": "Global Horizon College of Engineering",
                "program": "ENGINEERING_AND_TECHNOLOGY",
                "students": 200,
                "declared_land": 3.5,
                "deed_land": 3.5,
                "prof": 1,
                "assoc_prof": 3,
                "asst_prof": 8,
                "fire_expiry": "10-10-2026",
                "qr_url": "http://untrusted-external-domain.biz/fake_verify?id=99812",
                "tampered_date": False,
                "expected_status": "UNTRUSTED_QR_DESTINATION",
            },
        ]

        benchmarks = []
        for s in scenarios:
            inst_dir = self.base_dir / s["id"]
            inst_dir.mkdir(parents=True, exist_ok=True)

            # 1. Fire NOC PDF
            self.generate_fire_noc_pdf(
                filepath=inst_dir / "Fire_Safety_NOC.pdf",
                institution_name=s["name"],
                clearance_no=f"FS-{s['id']}-NOC",
                issue_date="15-06-2024",
                expiry_date=s["fire_expiry"],
                qr_payload=s["qr_url"],
                tampered_year_overlay=s["tampered_date"],
            )

            # 2. Land Title Deed PDF
            self.generate_land_title_deed_pdf(
                filepath=inst_dir / "Land_Title_Deed.pdf",
                institution_name=s["name"],
                survey_numbers="Sy. No. 142/1, 142/2A",
                registered_acres=s["deed_land"],
            )

            # 3. Faculty Portfolio PDF
            self.generate_faculty_portfolio_pdf(
                filepath=inst_dir / "Faculty_Portfolio.pdf",
                institution_name=s["name"],
                professors=s["prof"],
                assoc_professors=s["assoc_prof"],
                asst_professors=s["asst_prof"],
                total_students=s["students"],
            )

            # 4. Application JSON summary
            app_meta = {
                "application_id": f"APP-2024-{s['id']}",
                "institution_name": s["name"],
                "declared_land_acres": s["declared_land"],
                "total_approved_students": s["students"],
                "expected_status": s["expected_status"],
            }
            with open(inst_dir / "application_metadata.json", "w", encoding="utf-8") as f:
                json.dump(app_meta, f, indent=2)

            benchmarks.append(app_meta)

        # Write master ground_truth.json
        with open(self.base_dir / "ground_truth.json", "w", encoding="utf-8") as f:
            json.dump({"benchmarks": benchmarks}, f, indent=2)

        return len(scenarios)


if __name__ == "__main__":
    out = str(Path(__file__).parent.parent.parent / "data" / "synthetic_scenarios")
    gen = SyntheticDatasetGenerator(out)
    count = gen.build_all_scenarios()
    print(f"Generated {count} synthetic test scenarios in {out}")
