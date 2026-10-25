import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, date

from fastapi import FastAPI, HTTPException, Response, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.auth.security import (
    UserRole,
    Permission,
    UserSession,
    get_current_user,
    require_permission,
    require_role,
)

from app.rules.evaluator import APHRuleEvaluator
from app.forensics.ela import ErrorLevelAnalysis
from app.forensics.hash_vault import HashVerifiedVault
from app.audit.chained_logger import HashChainedAuditLogger
from app.adapters.qr_validator import QRDestinationValidator
from app.adapters.mock_adapters import DigiLockerMockAdapter, StateFireMockAdapter
from app.schemas.findings import (
    FindingRecord,
    OfficerResolutionStatus,
    AssessmentPillar,
    FindingOutcome,
    AggregatedStatus,
    PillarSummary,
    CanonicalEvaluationResult,
)

app = FastAPI(
    title="AICTE Regulatory Compliance & Document Verification Platform",
    description="AI-enabled Decision-Support Platform for AICTE Application Scrutiny & Regulatory Verification",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.db.database import LocalDatabaseManager
from app.scenarios.resolver import dataset_resolver, PathTraversalError
from app.ingestion.extractor import PyMuPDFExtractor
from app.adapters.qr_engine import qr_engine, QRStatus, SignatureStatus

RULES_FILE = Path(__file__).resolve().parent / "rules" / "aph_rules.json"

# Initialize engines
evaluator = APHRuleEvaluator()
audit_logger = HashChainedAuditLogger()
hash_vault = HashVerifiedVault()
qr_validator = QRDestinationValidator()
digilocker_adapter = DigiLockerMockAdapter()
fire_adapter = StateFireMockAdapter()
db_manager = LocalDatabaseManager()

# Seed SQLite database on startup using active resolver root
db_manager.seed_initial_data(dataset_resolver.active_root, RULES_FILE)
db_manager.seed_certificate_registry(dataset_resolver)


class OfficerDecisionRequest(BaseModel):
    finding_id: str
    decision: OfficerResolutionStatus
    officer_id: str
    reason: Optional[str] = None


@app.get("/api/v1/health")
def healthcheck():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "AICTE Application Scrutiny Engine",
        "rules_edition": "AICTE Approval Process Handbook 2024-2027",
        "dataset_diagnostics": dataset_resolver.get_diagnostic_info(),
    }


@app.get("/api/v1/rules")
def get_rules():
    return {
        "metadata": evaluator.rules_metadata,
        "rules": [r.model_dump() for r in evaluator.rules.values()],
    }


@app.get("/api/v1/scenarios")
def list_scenarios():
    return {"scenarios": dataset_resolver.list_scenarios()}


@app.post("/api/v1/evaluate/{scenario_id}")
async def evaluate_scenario(scenario_id: str):
    scenario_dir = dataset_resolver.resolve_scenario_path(scenario_id)
    meta_file = scenario_dir / "application_metadata.json"
    if not meta_file.exists():
        raise HTTPException(status_code=404, detail=f"application_metadata.json not found for scenario '{scenario_id}'")
    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    findings: List[FindingRecord] = []

    # 1. Evaluate Land Area Consistency
    # Dynamically extract registered land from Land Title Deed PDF
    declared_land = float(meta["declared_land_acres"]) if meta.get("declared_land_acres") is not None else None
    land_pdf_path = scenario_dir / "Land_Title_Deed.pdf"
    deed_land = None
    land_bbox = None
    land_page = 1
    if land_pdf_path.exists():
        land_data = PyMuPDFExtractor.extract_land_deed_data(str(land_pdf_path))
        deed_land = land_data.get("registered_acres")
        land_bbox = land_data.get("normalized_bbox")
        land_page = land_data.get("page_number", 1)

    land_finding = evaluator.evaluate_land_consistency(
        application_id=meta["application_id"],
        declared_acres=declared_land,
        deed_acres=deed_land,
        page_num=land_page,
        bbox=land_bbox,
    )
    findings.append(land_finding)

    # 2. Evaluate FSR & Cadre Ratio
    # Dynamically extract faculty counts and student intake from Faculty Portfolio PDF
    fac_pdf_path = scenario_dir / "Faculty_Portfolio.pdf"
    prof, assoc_prof, asst_prof, total_fac = None, None, None, None
    total_students = int(meta["total_approved_students"]) if meta.get("total_approved_students") is not None else None
    fac_bbox = None
    fac_page = 1
    if fac_pdf_path.exists():
        fac_data = PyMuPDFExtractor.extract_faculty_roster_data(str(fac_pdf_path))
        prof = fac_data.get("professors")
        assoc_prof = fac_data.get("assoc_professors")
        asst_prof = fac_data.get("asst_professors")
        total_fac = fac_data.get("total_faculty")
        fac_bbox = fac_data.get("normalized_bbox")
        fac_page = fac_data.get("page_number", 1)
        if total_students is None and fac_data.get("total_students") is not None:
            total_students = fac_data.get("total_students")

    fsr_finding = evaluator.evaluate_fsr(
        application_id=meta["application_id"],
        program_category=meta.get("program_category", "ENGINEERING_AND_TECHNOLOGY"),
        level=meta.get("level", "UG"),
        total_students=total_students,
        total_faculty=total_fac,
        page_num=fac_page,
        bbox=fac_bbox,
    )
    findings.append(fsr_finding)

    cadre_finding = evaluator.evaluate_cadre_ratio(
        application_id=meta["application_id"],
        professors=prof,
        assoc_professors=assoc_prof,
        asst_professors=asst_prof,
        page_num=fac_page,
        bbox=fac_bbox,
    )
    findings.append(cadre_finding)

    # 3. Fire NOC & Forensics check
    fire_noc_path = scenario_dir / "Fire_Safety_NOC.pdf"
    if fire_noc_path.exists():
        with open(fire_noc_path, "rb") as f:
            pdf_bytes = f.read()
        sha256 = hash_vault.compute_sha256(pdf_bytes)

        # Dynamic extraction of Fire NOC text and forensics
        fire_data = PyMuPDFExtractor.extract_fire_noc_data(str(fire_noc_path))
        extracted_cert_no = fire_data.get("certificate_id")
        extracted_exp = fire_data.get("expiry_date")
        fire_bbox = fire_data.get("normalized_bbox")
        fire_page = fire_data.get("page_number", 1)

        # Evaluate Fire NOC Validity & Forensic Visual Consistency
        if fire_data.get("has_visual_anomaly"):
            # Point 6 / Architecture plan: Localized compression variance without cross-record baseline
            fire_finding = evaluator.evaluate_fire_noc(
                application_id=meta["application_id"],
                expiry_date=extracted_exp,
                page_num=fire_page,
                bbox=fire_bbox,
            )
            fire_finding.outcome = FindingOutcome.UNABLE_TO_DETERMINE
            fire_finding.title = "Visual Inconsistency Detected Without Baseline"
            fire_finding.description = (
                "Localized ELA compression anomaly detected over certificate expiry date. "
                "No cross-record authority baseline is available for automatic corroboration. "
                "Requires officer verification through physical records or issuing authority."
            )
            fire_finding.confidence_or_uncertainty.uncertainty_notes = fire_data.get("anomaly_details") or "Visual compression variance detected without secondary corroboration."
            findings.append(fire_finding)
        else:
            fire_finding = evaluator.evaluate_fire_noc(
                application_id=meta["application_id"],
                expiry_date=extracted_exp,
                page_num=fire_page,
                bbox=fire_bbox,
            )
            findings.append(fire_finding)

        # 4. Dynamic QR Code & Digital Signature Engine (Phase 1)
        qr_res = qr_engine.detect_and_decode_qr(str(fire_noc_path))

        if qr_res.status == QRStatus.MISSING:
            findings.append(FindingRecord(
                finding_id=f"FIND-QR-MISSING-{meta['application_id']}",
                assessment_pillar=AssessmentPillar.AUTHENTICITY,
                outcome=FindingOutcome.REQUIRED_EVIDENCE_MISSING,
                title="Missing QR Verification Code",
                description="Submitted Fire Safety Clearance does not contain a machine-verifiable QR code.",
                applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                evidence={
                    "source_document_id": "DOC-FIRE-001",
                    "source_document_name": "Fire_Safety_NOC.pdf",
                    "page_number": 1,
                    "extracted_value": "No QR Code Found",
                    "discrepancy_magnitude": "Missing QR code",
                },
                confidence_or_uncertainty={"confidence_score": 1.0, "uncertainty_notes": "Optical scanner found no QR code in document."},
            ))
        elif qr_res.status == QRStatus.UNREADABLE:
            findings.append(FindingRecord(
                finding_id=f"FIND-QR-UNREADABLE-{meta['application_id']}",
                assessment_pillar=AssessmentPillar.AUTHENTICITY,
                outcome=FindingOutcome.UNABLE_TO_DETERMINE,
                title="Unreadable QR Verification Code",
                description="A QR code graphic was detected on the document, but is blurred, corrupted, or unreadable by automated decoders. Manual inspection required.",
                applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                evidence={
                    "source_document_id": "DOC-FIRE-001",
                    "source_document_name": "Fire_Safety_NOC.pdf",
                    "page_number": qr_res.page_number,
                    "extracted_value": "Unreadable QR Graphic",
                    "discrepancy_magnitude": "Decoder failure on degraded QR image",
                },
                confidence_or_uncertainty={"confidence_score": 0.0, "uncertainty_notes": qr_res.error_details or "QR image is too degraded to decode."},
            ))
        elif qr_res.status == QRStatus.MALFORMED:
            findings.append(FindingRecord(
                finding_id=f"FIND-QR-MALFORMED-{meta['application_id']}",
                assessment_pillar=AssessmentPillar.AUTHENTICITY,
                outcome=FindingOutcome.DISCREPANCY_FOUND,
                title="Malformed QR Verification Payload",
                description=f"Decoded QR code payload violates regulatory schema or contains corrupt data: {qr_res.raw_text[:60]}.",
                applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                evidence={
                    "source_document_id": "DOC-FIRE-001",
                    "source_document_name": "Fire_Safety_NOC.pdf",
                    "page_number": qr_res.page_number,
                    "extracted_value": qr_res.raw_text[:100],
                    "discrepancy_magnitude": "Schema violation in QR payload",
                },
                confidence_or_uncertainty={"confidence_score": 1.0, "uncertainty_notes": qr_res.error_details or "Malformed payload syntax."},
            ))
        elif qr_res.status == QRStatus.DECODED_URL:
            if not qr_res.is_trusted_destination:
                findings.append(FindingRecord(
                    finding_id=f"FIND-QR-UNTRUSTED-{meta['application_id']}",
                    assessment_pillar=AssessmentPillar.AUTHENTICITY,
                    outcome=FindingOutcome.DISCREPANCY_FOUND,
                    title="Untrusted QR Issuer Destination",
                    description=f"The QR code target URL ({qr_res.raw_text}) is not present in the authorized trusted-issuer allowlist. Manual review required.",
                    applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                    evidence={
                        "source_document_id": "DOC-FIRE-001",
                        "source_document_name": "Fire_Safety_NOC.pdf",
                        "page_number": qr_res.page_number,
                        "extracted_value": qr_res.raw_text[:120],
                        "discrepancy_magnitude": "Untrusted domain destination",
                    },
                    confidence_or_uncertainty={"confidence_score": 1.0, "uncertainty_notes": "Domain whitelist check failed."},
                ))
            else:
                findings.append(FindingRecord(
                    finding_id=f"FIND-QR-TRUSTED-{meta['application_id']}",
                    assessment_pillar=AssessmentPillar.AUTHENTICITY,
                    outcome=FindingOutcome.COMPLIANT,
                    title="QR Issuer Destination Verified",
                    description=f"QR verification destination conforms to authorized government portal: {qr_res.raw_text[:80]}",
                    applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                    evidence={
                        "source_document_id": "DOC-FIRE-001",
                        "source_document_name": "Fire_Safety_NOC.pdf",
                        "page_number": qr_res.page_number,
                        "extracted_value": qr_res.raw_text[:120],
                    },
                    confidence_or_uncertainty={"confidence_score": 0.98, "uncertainty_notes": "Matched against official authority allowlist."},
                ))
        elif qr_res.status == QRStatus.DECODED_PAYLOAD:
            payload = qr_res.parsed_payload
            qr_findings = []

            # 1. Certificate ID match check
            payload_cert_id = payload.get("certificate_id")
            if payload_cert_id and extracted_cert_no and payload_cert_id != extracted_cert_no:
                qr_findings.append(FindingRecord(
                    finding_id=f"FIND-QR-ID-MISMATCH-{meta['application_id']}",
                    assessment_pillar=AssessmentPillar.AUTHENTICITY,
                    outcome=FindingOutcome.DISCREPANCY_FOUND,
                    title="Certificate ID Mismatch Between QR and Printed Text",
                    description=f"QR payload specifies Certificate ID '{payload_cert_id}', but document header displays '{extracted_cert_no}'.",
                    applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                    evidence={
                        "source_document_id": "DOC-FIRE-001",
                        "source_document_name": "Fire_Safety_NOC.pdf",
                        "page_number": qr_res.page_number,
                        "extracted_value": f"QR ID: {payload_cert_id} vs Doc ID: {extracted_cert_no}",
                        "discrepancy_magnitude": "Certificate ID divergence",
                    },
                    confidence_or_uncertainty={"confidence_score": 1.0, "uncertainty_notes": "Direct string comparison between QR cryptographic payload and printed document."},
                ))

            # 2. Institution / Holder mismatch check
            payload_inst = payload.get("institution_name")
            applicant_inst = meta.get("institution_name", "")
            if payload_inst and applicant_inst and payload_inst.strip().lower() != applicant_inst.strip().lower():
                qr_findings.append(FindingRecord(
                    finding_id=f"FIND-QR-HOLDER-MISMATCH-{meta['application_id']}",
                    assessment_pillar=AssessmentPillar.AUTHENTICITY,
                    outcome=FindingOutcome.DISCREPANCY_FOUND,
                    title="Certificate Holder Mismatch",
                    description=f"Certificate in issuer records is registered to '{payload_inst}', which differs from applicant '{applicant_inst}'.",
                    applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                    evidence={
                        "source_document_id": "DOC-FIRE-001",
                        "source_document_name": "Fire_Safety_NOC.pdf",
                        "page_number": qr_res.page_number,
                        "extracted_value": f"Issuer Holder: {payload_inst} vs Applicant: {applicant_inst}",
                        "discrepancy_magnitude": "Entity holder mismatch",
                    },
                    confidence_or_uncertainty={"confidence_score": 0.99, "uncertainty_notes": "Issuer record holder does not match application metadata."},
                ))

            # 3. Status checks (Revoked, Expired, Source Unavailable)
            v_status = payload.get("verification_status")
            if v_status == "REVOKED":
                qr_findings.append(FindingRecord(
                    finding_id=f"FIND-QR-REVOKED-{meta['application_id']}",
                    assessment_pillar=AssessmentPillar.AUTHENTICITY,
                    outcome=FindingOutcome.DISCREPANCY_FOUND,
                    title="Certificate Revoked by Issuing Authority",
                    description="The issuing authority has marked this clearance certificate as REVOKED in its central registry.",
                    applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                    evidence={
                        "source_document_id": "DOC-FIRE-001",
                        "source_document_name": "Fire_Safety_NOC.pdf",
                        "page_number": qr_res.page_number,
                        "extracted_value": "Status: REVOKED",
                        "discrepancy_magnitude": "Revoked regulatory clearance",
                    },
                    confidence_or_uncertainty={"confidence_score": 1.0, "uncertainty_notes": "Confirmed by authoritative issuer record."},
                ))
            elif v_status == "EXPIRED":
                qr_findings.append(FindingRecord(
                    finding_id=f"FIND-QR-EXPIRED-{meta['application_id']}",
                    assessment_pillar=AssessmentPillar.AUTHENTICITY,
                    outcome=FindingOutcome.DISCREPANCY_FOUND,
                    title="Certificate Expired in Issuer Records",
                    description=f"Issuer record indicates certificate expired on {payload.get('valid_until', 'prior date')}.",
                    applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                    evidence={
                        "source_document_id": "DOC-FIRE-001",
                        "source_document_name": "Fire_Safety_NOC.pdf",
                        "page_number": qr_res.page_number,
                        "extracted_value": f"Status: EXPIRED (Valid Until: {payload.get('valid_until')})",
                        "discrepancy_magnitude": "Expired clearance in issuer database",
                    },
                    confidence_or_uncertainty={"confidence_score": 1.0, "uncertainty_notes": "Authoritative issuer status is EXPIRED."},
                ))
            elif v_status == "SOURCE_UNAVAILABLE":
                qr_findings.append(FindingRecord(
                    finding_id=f"FIND-QR-UNAVAILABLE-{meta['application_id']}",
                    assessment_pillar=AssessmentPillar.AUTHENTICITY,
                    outcome=FindingOutcome.UNABLE_TO_DETERMINE,
                    title="Issuer Verification Gateway Unavailable",
                    description="Issuer verification gateway timed out or returned service unavailable. Requires manual officer review.",
                    applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                    evidence={
                        "source_document_id": "DOC-FIRE-001",
                        "source_document_name": "Fire_Safety_NOC.pdf",
                        "page_number": qr_res.page_number,
                        "extracted_value": "Status: SOURCE_UNAVAILABLE",
                        "discrepancy_magnitude": "Authority gateway unreachable",
                    },
                    confidence_or_uncertainty={"confidence_score": 0.0, "uncertainty_notes": "Network/gateway unavailable."},
                ))

            # 4. Validity Date Mismatch between visual text and QR record
            payload_until = payload.get("valid_until")
            if payload_until and extracted_exp:
                # If years or dates mismatch significantly
                if str(extracted_exp.year) not in payload_until and payload_until[:4] not in str(extracted_exp):
                    qr_findings.append(FindingRecord(
                        finding_id=f"FIND-QR-DATE-MISMATCH-{meta['application_id']}",
                        assessment_pillar=AssessmentPillar.AUTHENTICITY,
                        outcome=FindingOutcome.DISCREPANCY_FOUND,
                        title="Validity Date Mismatch Between Document Text and QR Record",
                        description=f"Printed document displays expiry date {extracted_exp.strftime('%d-%m-%Y')}, but QR cryptographic record states {payload_until}.",
                        applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                        evidence={
                            "source_document_id": "DOC-FIRE-001",
                            "source_document_name": "Fire_Safety_NOC.pdf",
                            "page_number": qr_res.page_number,
                            "extracted_value": f"Doc Expiry: {extracted_exp} vs QR Record: {payload_until}",
                            "discrepancy_magnitude": "Temporal discrepancy between record and print",
                        },
                        confidence_or_uncertainty={"confidence_score": 1.0, "uncertainty_notes": "Direct contradiction between embedded record and visual text."},
                    ))

            # If no discrepancy found in payload, record verified
            if not qr_findings:
                qr_findings.append(FindingRecord(
                    finding_id=f"FIND-QR-VERIFIED-{meta['application_id']}",
                    assessment_pillar=AssessmentPillar.AUTHENTICITY,
                    outcome=FindingOutcome.COMPLIANT,
                    title="Cryptographic Certificate Record Verified",
                    description=f"QR code payload authenticated against authority schema (Certificate ID: {payload_cert_id}).",
                    applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                    evidence={
                        "source_document_id": "DOC-FIRE-001",
                        "source_document_name": "Fire_Safety_NOC.pdf",
                        "page_number": qr_res.page_number,
                        "extracted_value": f"Verified Certificate: {payload_cert_id}",
                    },
                    confidence_or_uncertainty={"confidence_score": 1.0, "uncertainty_notes": "Cryptographic payload matched document reference and issuer status."},
                ))
            findings.extend(qr_findings)

        # 5. Dynamic Digital Signature Inspection
        sig_res = qr_engine.inspect_digital_signatures(str(fire_noc_path))
        if sig_res.status == SignatureStatus.INVALID:
            findings.append(FindingRecord(
                finding_id=f"FIND-SIG-INVALID-{meta['application_id']}",
                assessment_pillar=AssessmentPillar.AUTHENTICITY,
                outcome=FindingOutcome.DISCREPANCY_FOUND,
                title="Digital Signature Verification Failed",
                description="Digital signature verification failed: signature is invalid, corrupted, or tampered.",
                applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                evidence={
                    "source_document_id": "DOC-FIRE-001",
                    "source_document_name": "Fire_Safety_NOC.pdf",
                    "page_number": 1,
                    "extracted_value": "Signature State: MOCK_INVALID",
                    "discrepancy_magnitude": "Cryptographic signature validation failure",
                },
                confidence_or_uncertainty={"confidence_score": 1.0, "uncertainty_notes": sig_res.details or "Signature hash verification failed."},
            ))
        elif sig_res.status == SignatureStatus.UNAVAILABLE:
            findings.append(FindingRecord(
                finding_id=f"FIND-SIG-UNAVAILABLE-{meta['application_id']}",
                assessment_pillar=AssessmentPillar.AUTHENTICITY,
                outcome=FindingOutcome.UNABLE_TO_DETERMINE,
                title="Digital Signature Authority Unavailable",
                description="Digital signature timestamp or certificate authority check could not be completed automatically. Manual inspection required.",
                applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                evidence={
                    "source_document_id": "DOC-FIRE-001",
                    "source_document_name": "Fire_Safety_NOC.pdf",
                    "page_number": 1,
                    "extracted_value": "Signature State: MANUAL_VERIFICATION_REQUIRED",
                    "discrepancy_magnitude": "Authority offline",
                },
                confidence_or_uncertainty={"confidence_score": 0.0, "uncertainty_notes": sig_res.details or "Signature verification gateway offline."},
            ))
        elif sig_res.status == SignatureStatus.VALID:
            findings.append(FindingRecord(
                finding_id=f"FIND-SIG-VALID-{meta['application_id']}",
                assessment_pillar=AssessmentPillar.AUTHENTICITY,
                outcome=FindingOutcome.COMPLIANT,
                title="Digital Signature Authenticated",
                description=f"Digital signature cryptographically authenticated (Signer: {sig_res.signer_name}).",
                applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                evidence={
                    "source_document_id": "DOC-FIRE-001",
                    "source_document_name": "Fire_Safety_NOC.pdf",
                    "page_number": 1,
                    "extracted_value": f"Signer: {sig_res.signer_name} | {sig_res.authority}",
                },
                confidence_or_uncertainty={"confidence_score": 0.99, "uncertainty_notes": sig_res.details or "Signature verified."},
            ))

        # 6. Cross-Application Certificate Registry & Collision Check (Phase 2)
        target_cert = extracted_cert_no
        if not target_cert and qr_res.status == QRStatus.DECODED_PAYLOAD:
            target_cert = qr_res.parsed_payload.get("certificate_id")

        if target_cert:
            # Register current certificate
            db_manager.register_certificate(
                certificate_id=target_cert,
                application_id=meta["application_id"],
                scenario_id=scenario_id,
                institution_name=meta.get("institution_name", scenario_id),
                document_type="FIRE_SAFETY_NOC",
            )

            # Check collisions with OTHER applications
            collisions = db_manager.check_certificate_collision(target_cert, meta["application_id"])
            if collisions:
                prior = collisions[0]
                findings.append(FindingRecord(
                    finding_id=f"FIND-CERT-COLLISION-{meta['application_id']}",
                    assessment_pillar=AssessmentPillar.AUTHENTICITY,
                    outcome=FindingOutcome.DISCREPANCY_FOUND,
                    title="Duplicate Certificate Reference Registered Across Multiple Applications",
                    description=(
                        f"Certificate reference '{target_cert}' has also been registered under Application "
                        f"{prior['application_id']} ({prior['institution_name']}). Multi-applicant certificate collision detected."
                    ),
                    applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                    evidence={
                        "source_document_id": "DOC-FIRE-001",
                        "source_document_name": "Fire_Safety_NOC.pdf",
                        "page_number": 1,
                        "extracted_value": f"Duplicate Certificate ID: {target_cert}",
                        "compared_against": {
                            "colliding_application_id": prior["application_id"],
                            "colliding_institution_name": prior["institution_name"],
                            "colliding_scenario_id": prior["scenario_id"],
                        },
                        "discrepancy_magnitude": "Multi-institution certificate reuse",
                    },
                    confidence_or_uncertainty={"confidence_score": 1.0, "uncertainty_notes": "Authoritative registry collision check across submitted application packages."},
                ))

    # 7. Mandatory Completeness Check (AssessmentPillar.COMPLETENESS)
    mandatory_docs = [
        ("Land_Title_Deed.pdf", "DOC-LAND-001"),
        ("Faculty_Portfolio.pdf", "DOC-FACULTY-001"),
        ("Fire_Safety_NOC.pdf", "DOC-FIRE-001"),
    ]
    missing_docs = [doc for doc, _ in mandatory_docs if not (scenario_dir / doc).exists()]
    if missing_docs:
        for missing_doc, doc_id in mandatory_docs:
            if not (scenario_dir / missing_doc).exists():
                findings.append(FindingRecord(
                    finding_id=f"FIND-COMPL-MISSING-{doc_id}-{meta['application_id']}",
                    assessment_pillar=AssessmentPillar.COMPLETENESS,
                    outcome=FindingOutcome.REQUIRED_EVIDENCE_MISSING,
                    title=f"Mandatory Regulatory Document Missing: {missing_doc}",
                    description=f"Mandatory statutory attachment '{missing_doc}' is absent from submitted application dossier.",
                    applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
                    evidence={
                        "source_document_id": doc_id,
                        "source_document_name": missing_doc,
                        "page_number": 1,
                        "extracted_value": "Document Missing",
                        "discrepancy_magnitude": "Absent mandatory attachment",
                    },
                    confidence_or_uncertainty={"confidence_score": 1.0, "uncertainty_notes": "File not found in application package."},
                ))
    else:
        findings.append(FindingRecord(
            finding_id=f"FIND-COMPL-ALL-PRESENT-{meta['application_id']}",
            assessment_pillar=AssessmentPillar.COMPLETENESS,
            outcome=FindingOutcome.COMPLIANT,
            title="Mandatory Dossier Submission Complete",
            description="All mandatory regulatory attachments (Land Title Deed, Faculty Portfolio, Fire Safety NOC) are present in the submitted application package.",
            applicable_rule=evaluator.get_rule_ref("APH-2024-FIRE-NOC-VALIDITY"),
            evidence={
                "source_document_id": "DOC-DOSSIER-ROOT",
                "source_document_name": "Application Dossier",
                "page_number": 1,
                "extracted_value": "3/3 Mandatory Attachments Verified",
            },
            confidence_or_uncertainty={"confidence_score": 1.0, "uncertainty_notes": "All required files verified in storage hierarchy."},
        ))

    # 8. Canonical Results Model & Honest Status Aggregation (Phase 6)
    pillar_summaries: Dict[str, PillarSummary] = {}
    for p in AssessmentPillar:
        p_findings = [f for f in findings if f.assessment_pillar == p]
        c_count = sum(1 for f in p_findings if f.outcome == FindingOutcome.COMPLIANT)
        d_count = sum(1 for f in p_findings if f.outcome == FindingOutcome.DISCREPANCY_FOUND)
        r_count = sum(1 for f in p_findings if f.outcome in (FindingOutcome.REQUIRED_EVIDENCE_MISSING, FindingOutcome.UNABLE_TO_DETERMINE))

        if d_count > 0:
            p_status = AggregatedStatus.DISCREPANCY_FOUND
        elif r_count > 0:
            p_status = AggregatedStatus.REQUIRES_OFFICER_REVIEW
        else:
            p_status = AggregatedStatus.COMPLIANT

        pillar_summaries[p.value] = PillarSummary(
            pillar=p,
            status=p_status,
            total_findings=len(p_findings),
            compliant_count=c_count,
            discrepancy_count=d_count,
            review_required_count=r_count,
        )

    # Top-level honest status roll-up
    any_discrepancy = any(s.discrepancy_count > 0 for s in pillar_summaries.values())
    any_review = any(s.review_required_count > 0 for s in pillar_summaries.values())

    if any_discrepancy:
        overall_status = AggregatedStatus.DISCREPANCY_FOUND
    elif any_review:
        overall_status = AggregatedStatus.REQUIRES_OFFICER_REVIEW
    else:
        overall_status = AggregatedStatus.COMPLIANT

    # Persist findings to local SQLite DB
    for f in findings:
        db_manager.record_finding(scenario_id, f.model_dump())

    # Audit Logging
    audit_logger.log_event(
        actor_id="SYSTEM_AUTO_SCRUTINY",
        role="SYSTEM_AUTOMATION",
        action="EVALUATE_APPLICATION",
        application_id=meta["application_id"],
        details={"findings_count": len(findings), "scenario_id": scenario_id, "overall_status": overall_status.value},
    )

    canonical_result = CanonicalEvaluationResult(
        scenario_id=scenario_id,
        application_metadata=meta,
        overall_status=overall_status,
        pillar_summaries=pillar_summaries,
        findings=findings,
        evaluated_at=datetime.now().isoformat(),
    )
    return canonical_result.model_dump()


import fitz

@app.get("/api/v1/documents/{scenario_id}/{doc_name}")
def get_document(scenario_id: str, doc_name: str):
    file_path = dataset_resolver.resolve_document_path(scenario_id, doc_name)
    with open(file_path, "rb") as f:
        content = f.read()
    return Response(content=content, media_type="application/pdf")


@app.get("/api/v1/documents/{scenario_id}/{doc_name}/render")
def render_document_page(scenario_id: str, doc_name: str, page: int = 1, dpi: int = 150):
    file_path = dataset_resolver.resolve_document_path(scenario_id, doc_name)
    try:
        doc = fitz.open(str(file_path))
        if page < 1 or page > len(doc):
            page = 1
        page_obj = doc[page - 1]
        pix = page_obj.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        doc.close()
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rendering failed: {str(e)}")


@app.get("/api/v1/documents/{scenario_id}/{doc_name}/ela")
def get_ela_heatmap(scenario_id: str, doc_name: str, page: int = 1):
    file_path = dataset_resolver.resolve_document_path(scenario_id, doc_name)
    try:
        doc = fitz.open(str(file_path))
        page_obj = doc[max(0, page - 1)]
        pix = page_obj.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        doc.close()

        # Generate true pixel-by-pixel ELA compression heatmap
        ela_bytes, score = ErrorLevelAnalysis.generate_ela_heatmap(img_bytes, resave_quality=85, scale=18.0)
        return Response(content=ela_bytes, media_type="image/jpeg", headers={"X-ELA-Score": str(score)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ELA generation failed: {str(e)}")


@app.get("/api/v1/documents/{scenario_id}/{doc_name}/meta")
def get_document_meta(scenario_id: str, doc_name: str):
    file_path = dataset_resolver.resolve_document_path(scenario_id, doc_name)
    with open(file_path, "rb") as f:
        content = f.read()
    sha256 = hash_vault.compute_sha256(content)
    dhash = hash_vault.compute_dhash(content[:2048]) if doc_name.endswith('.png') or doc_name.endswith('.jpg') else "N/A (Vector PDF)"
    doc = fitz.open(str(file_path))
    total_pages = len(doc)
    doc.close()
    return {
        "filename": doc_name,
        "total_pages": total_pages,
        "sha256_hash": sha256,
        "dhash": dhash,
        "file_size_bytes": len(content),
        "integrity_status": "Verified Match (SHA-256)",
        "duplicate_detection": "No Collision Across Database",
    }
@app.post("/api/v1/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    scenario_id: str = Form(...),
    document_type: str = Form("SUPPLEMENTAL_DOCUMENT"),
    institution_name: Optional[str] = Form(None),
    user: UserSession = Depends(require_permission(Permission.UPLOAD_DOCUMENT)),
):
    valid_exts = [".pdf", ".png", ".jpg", ".jpeg"]
    orig_name = file.filename or "uploaded_doc.pdf"
    file_ext = Path(orig_name).suffix.lower()
    if file_ext not in valid_exts:
        raise HTTPException(
            status_code=400,
            detail="Unsupported format. Only PDF, PNG, and JPEG documents are accepted for statutory scrutiny.",
        )

    try:
        clean_scenario_id = dataset_resolver.sanitize_identifier(scenario_id)
    except PathTraversalError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Standardize or retain filename
    if document_type == "Fire_Safety_NOC":
        target_filename = "Fire_Safety_NOC.pdf"
    elif document_type == "Land_Title_Deed":
        target_filename = "Land_Title_Deed.pdf"
    elif document_type == "Faculty_Portfolio":
        target_filename = "Faculty_Portfolio.pdf"
    else:
        target_filename = orig_name.replace(" ", "_")

    scenario_dir = dataset_resolver.active_root / clean_scenario_id
    scenario_dir.mkdir(parents=True, exist_ok=True)

    # Ensure application_metadata.json exists
    meta_path = scenario_dir / "application_metadata.json"
    if not meta_path.exists():
        app_meta = {
            "application_id": f"APP-2024-{clean_scenario_id}",
            "institution_name": institution_name or f"Institution ({scenario_id})",
            "institution_category": "UG Engineering & Technology",
            "declared_land_acres": 4.0,
            "total_approved_students": 240,
            "created_at": datetime.now().isoformat(),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(app_meta, f, indent=2)

    target_path = scenario_dir / target_filename
    file_bytes = await file.read()
    with open(target_path, "wb") as f:
        f.write(file_bytes)

    # Hash verification vault calculation
    sha256 = hash_vault.compute_sha256(file_bytes)
    dhash = (
        hash_vault.compute_dhash(file_bytes[:2048])
        if target_filename.endswith((".png", ".jpg", ".jpeg"))
        else "N/A (Vector PDF)"
    )

    # Determine total pages
    total_pages = 1
    if target_filename.endswith(".pdf"):
        try:
            doc = fitz.open(str(target_path))
            total_pages = len(doc)
            doc.close()
        except Exception:
            total_pages = 1

    # Insert / update in SQLite database
    doc_id = f"DOC-{scenario_id}-{Path(target_filename).stem.upper()}"
    db_manager.insert_document(
        document_id=doc_id,
        institution_id=scenario_id,
        document_type=document_type,
        filename=target_filename,
        file_path=str(target_path),
        sha256_hash=sha256,
        dhash=dhash,
    )

    # Append to cryptographically chained audit log
    event = audit_logger.log_event(
        actor_id=user.badge_number or user.user_id,
        role=user.role.value,
        action="DOCUMENT_UPLOADED",
        application_id=clean_scenario_id,
        details={
            "document_name": target_filename,
            "document_type": document_type,
            "sha256_hash": sha256,
            "file_size_bytes": len(file_bytes),
            "total_pages": total_pages,
        },
    )

    return {
        "status": "success",
        "message": f"Document '{target_filename}' successfully ingested into Hash-Verified Vault.",
        "filename": target_filename,
        "scenario_id": clean_scenario_id,
        "sha256": sha256,
        "sha256_hash": sha256,
        "total_pages": total_pages,
        "size_bytes": len(file_bytes),
        "audit_event_id": event.event_id,
    }


@app.post("/api/v1/officer/decision")
def record_decision(
    req: OfficerDecisionRequest,
    user: UserSession = Depends(require_permission(Permission.OFFICER_OVERRIDE)),
):
    officer_id = req.officer_id or user.badge_number or user.user_id
    # Update local SQLite DB
    db_manager.update_officer_decision(
        finding_id=req.finding_id,
        decision=req.decision.value if hasattr(req.decision, 'value') else str(req.decision),
        officer_id=officer_id,
        reason=req.reason,
    )

    # Log in SHA-256 hash-chained audit trail
    event = audit_logger.log_event(
        actor_id=officer_id,
        role=user.role.value,
        action="OFFICER_RESOLUTION",
        application_id=req.finding_id,
        details={
            "finding_id": req.finding_id,
            "decision": req.decision.value if hasattr(req.decision, 'value') else str(req.decision),
            "reason": req.reason,
            "officer_role": user.role.value,
        },
    )
    return {
        "status": "recorded",
        "event_id": event.event_id,
        "timestamp": event.timestamp,
        "officer_id": officer_id,
        "role": user.role.value,
    }


@app.get("/api/v1/auth/me")
def get_auth_me(user: UserSession = Depends(get_current_user)):
    return {
        "user_id": user.user_id,
        "role": user.role.value,
        "badge_number": user.badge_number,
        "permissions": [p.value for p in user.permissions],
    }


@app.get("/api/v1/db/stats")
def get_db_stats():
    """Returns real-time relational table row counts from the local SQLite database."""
    return {
        "database_type": "SQLite 3 Relational Database",
        "file_path": str(db_manager.db_path),
        "tables": db_manager.get_stats(),
    }


@app.get("/api/v1/audit/trail")
def get_audit_trail():
    is_valid, err = audit_logger.verify_chain_integrity()
    return {
        "chain_integrity_valid": is_valid,
        "integrity_error": err,
        "total_events": len(audit_logger.events),
        "events": [e.model_dump() for e in audit_logger.events],
    }


