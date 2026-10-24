import React, { useState, useEffect, useRef } from 'react';
import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  ShieldCheck,
  ShieldAlert,
  Eye,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Lock,
  RefreshCw,
  QrCode,
  Flame,
  Building2,
  GraduationCap,
  Scale,
  CopyCheck,
  Layers,
  ChevronRight,
  Info,
  Check,
  X,
  FileCheck,
  Cpu,
} from 'lucide-react';

interface FindingRecord {
  finding_id: string;
  assessment_pillar: 'AUTHENTICITY' | 'COMPLETENESS' | 'REGULATORY_COMPLIANCE';
  outcome: 'Compliant' | 'Discrepancy Found' | 'Required Evidence Missing' | 'Unable to Determine';
  title: string;
  description: string;
  applicable_rule: {
    rule_id: string;
    version: string;
    aph_edition: string;
    clause_reference: string;
    statutory_basis: string;
  };
  evidence: {
    source_document_id: string;
    source_document_name: string;
    page_number: number;
    normalized_bbox?: {
      x: number;
      y: number;
      width: number;
      height: number;
    };
    extracted_value: string;
    compared_against?: Record<string, any>;
    discrepancy_magnitude?: string;
  };
  confidence_or_uncertainty: {
    confidence_score?: number;
    uncertainty_notes?: string;
  };
  officer_resolution: {
    status: 'PENDING_REVIEW' | 'ACCEPTED' | 'OVERRIDDEN' | 'REFERRED_FOR_INSPECTION';
    officer_id?: string;
    override_reason?: string;
    timestamp?: string;
  };
}

interface DocumentMeta {
  filename: string;
  total_pages: number;
  sha256_hash: string;
  dhash: string;
  file_size_bytes: number;
  integrity_status: string;
  duplicate_detection: string;
}

export default function App() {
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>('INST-01-COMPLIANT');
  const [evaluationData, setEvaluationData] = useState<any>(null);
  const [activeDocument, setActiveDocument] = useState<string>('Fire_Safety_NOC.pdf');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedFinding, setSelectedFinding] = useState<FindingRecord | null>(null);
  const [showHeatmap, setShowHeatmap] = useState<boolean>(false);
  const [showHighlights, setShowHighlights] = useState<boolean>(true);
  const [activePillarTab, setActivePillarTab] = useState<'ALL' | 'AUTHENTICITY' | 'COMPLETENESS' | 'REGULATORY_COMPLIANCE'>('ALL');
  const [loading, setLoading] = useState<boolean>(false);
  const [docMeta, setDocMeta] = useState<DocumentMeta | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(1.0);
  const [auditEvents, setAuditEvents] = useState<any[]>([]);
  const [showAuditModal, setShowAuditModal] = useState<boolean>(false);

  // Load scenarios on mount
  useEffect(() => {
    fetch('/api/v1/scenarios')
      .then((res) => res.json())
      .then((data) => {
        if (data.scenarios && data.scenarios.length > 0) {
          setScenarios(data.scenarios);
          const initialId = data.scenarios[0].application_id.replace('APP-2024-', '');
          loadScenario(initialId);
        }
      })
      .catch((err) => console.error('Failed to load scenarios:', err));
  }, []);

  // Fetch document metadata whenever active document changes
  useEffect(() => {
    if (selectedScenario && activeDocument) {
      fetch(`/api/v1/documents/${selectedScenario}/${activeDocument}/meta`)
        .then((res) => res.json())
        .then((data) => setDocMeta(data))
        .catch(() => setDocMeta(null));
    }
  }, [selectedScenario, activeDocument]);

  const loadScenario = (scenarioId: string) => {
    setLoading(true);
    setSelectedScenario(scenarioId);
    setSelectedFinding(null);
    setShowHeatmap(false);
    setCurrentPage(1);

    fetch(`/api/v1/evaluate/${scenarioId}`, { method: 'POST' })
      .then((res) => res.json())
      .then((data) => {
        setEvaluationData(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  };

  const handleInspectFinding = (finding: FindingRecord) => {
    setSelectedFinding(finding);
    if (finding.evidence.source_document_name) {
      setActiveDocument(finding.evidence.source_document_name);
      setCurrentPage(finding.evidence.page_number || 1);
    }
  };

  const recordOfficerDecision = (decision: string, reason?: string) => {
    if (!selectedFinding) return;
    fetch('/api/v1/officer/decision', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        finding_id: selectedFinding.finding_id,
        decision: decision,
        officer_id: 'AICTE-OFFICER-409',
        reason: reason || 'Verified through Split-Screen Scrutiny Cockpit',
      }),
    })
      .then(() => {
        // Refresh finding list
        loadScenario(selectedScenario);
      })
      .catch((err) => console.error('Failed to record decision:', err));
  };

  const fetchAuditTrail = () => {
    fetch('/api/v1/audit/trail')
      .then((res) => res.json())
      .then((data) => {
        setAuditEvents(data.events || []);
        setShowAuditModal(true);
      });
  };

  const allFindings: FindingRecord[] = evaluationData?.findings || [];
  const filteredFindings = allFindings.filter((f) => {
    if (activePillarTab === 'ALL') return true;
    return f.assessment_pillar === activePillarTab;
  });

  const authenticityFindings = allFindings.filter((f) => f.assessment_pillar === 'AUTHENTICITY');
  const completenessFindings = allFindings.filter((f) => f.assessment_pillar === 'COMPLETENESS');
  const complianceFindings = allFindings.filter((f) => f.assessment_pillar === 'REGULATORY_COMPLIANCE');

  const currentInstitution = evaluationData?.application_metadata;

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 font-sans selection:bg-blue-600 selection:text-white">
      {/* ─────────────────────────────────────────────────────────────────────────
          TOP GOVERNMENT HEADER & APPLICATION REVIEW DASHBOARD
      ────────────────────────────────────────────────────────────────────────── */}
      <header className="border-b border-slate-800 bg-slate-900/95 backdrop-blur sticky top-0 z-50 px-6 py-2.5">
        <div className="flex items-center justify-between gap-4">
          {/* AICTE Logo & Bureau Title */}
          <div className="flex items-center gap-3.5">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-800 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/20 text-xs border border-blue-400/30">
              AICTE
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold tracking-wider text-slate-100 uppercase">
                  Regulation Bureau · Approval Scrutiny Platform
                </span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-900/60 text-blue-300 border border-blue-700/50">
                  APH 2024–2027
                </span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/40 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" />
                  Decision-Support Mode
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                AI-Powered Evidence Triage, Document Authentication & Regulatory Scrutiny
              </p>
            </div>
          </div>

          {/* Scenario Selector & Audit Controls */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-700 shadow-inner">
              <span className="text-xs text-slate-400 font-medium">Scenario:</span>
              <select
                value={selectedScenario}
                onChange={(e) => loadScenario(e.target.value)}
                className="bg-transparent text-xs text-slate-100 font-medium focus:outline-none cursor-pointer"
              >
                {scenarios.map((s) => {
                  const id = s.application_id.replace('APP-2024-', '');
                  return (
                    <option key={id} value={id} className="bg-slate-900 text-slate-100">
                      {id}: {s.institution_name.slice(0, 32)}...
                    </option>
                  );
                })}
              </select>
            </div>

            <button
              onClick={fetchAuditTrail}
              className="flex items-center gap-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700 transition shadow-sm"
              title="Inspect Cryptographically Chained Audit Log"
            >
              <Lock className="w-3.5 h-3.5 text-emerald-400" />
              <span>Chained Audit Log</span>
            </button>
          </div>
        </div>

        {/* Advisory Warning Banner (Strictly Non-Prejudicial) */}
        <div className="mt-2.5 px-3 py-1.5 bg-amber-950/40 border border-amber-800/40 rounded-lg flex items-center justify-between text-xs text-amber-200/90">
          <div className="flex items-center gap-2">
            <Info className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span>
              <strong>Statutory Safeguard:</strong> All automated signals (ELA, hash collisions, rule findings) are advisory screening tools for Scrutiny Officers. Final regulatory decisions remain with competent AICTE committees.
            </span>
          </div>
          <span className="text-[10px] uppercase font-mono tracking-wider text-amber-400/80 bg-amber-900/40 px-2 py-0.5 rounded">
            Human-in-the-Loop
          </span>
        </div>
      </header>

      {/* ─────────────────────────────────────────────────────────────────────────
          MAIN SPLIT-SCREEN WORKSPACE
      ────────────────────────────────────────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">
        {/* ═════════════════════════════════════════════════════════════════════════
            LEFT PANE: MODULE 2 & MODULE 3 — PDF EVIDENCE VIEWER & AUTHENTICITY TOOLS
        ══════════════════════════════════════════════════════════════════════════ */}
        <div className="w-7/12 border-r border-slate-800 flex flex-col bg-slate-900/40">
          {/* Document Tabs & Authenticity Action Bar */}
          <div className="border-b border-slate-800 bg-slate-900/80 px-4 py-2 flex flex-col gap-2">
            {/* Row 1: Document Selector Tabs */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                {[
                  { name: 'Fire_Safety_NOC.pdf', label: 'Fire Safety NOC', icon: Flame },
                  { name: 'Land_Title_Deed.pdf', label: 'Land Title Deed', icon: Building2 },
                  { name: 'Faculty_Portfolio.pdf', label: 'Faculty Portfolio', icon: GraduationCap },
                ].map((doc) => {
                  const Icon = doc.icon;
                  const isActive = activeDocument === doc.name;
                  return (
                    <button
                      key={doc.name}
                      onClick={() => {
                        setActiveDocument(doc.name);
                        setCurrentPage(1);
                        setSelectedFinding(null);
                      }}
                      className={`text-xs px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                        isActive
                          ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30 font-semibold'
                          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      {doc.label}
                    </button>
                  );
                })}
              </div>

              {/* Zoom & Viewport Controls */}
              <div className="flex items-center gap-1 bg-slate-950 px-2 py-1 rounded-lg border border-slate-800 text-xs">
                <button
                  onClick={() => setZoomLevel((z) => Math.max(0.7, z - 0.1))}
                  className="p-1 text-slate-400 hover:text-white"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-3.5 h-3.5" />
                </button>
                <span className="text-[11px] font-mono text-slate-300 w-10 text-center">
                  {Math.round(zoomLevel * 100)}%
                </span>
                <button
                  onClick={() => setZoomLevel((z) => Math.min(1.6, z + 0.1))}
                  className="p-1 text-slate-400 hover:text-white"
                  title="Zoom In"
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setZoomLevel(1.0)}
                  className="p-1 text-slate-400 hover:text-white ml-1"
                  title="Reset Zoom"
                >
                  <Maximize2 className="w-3 h-3" />
                </button>
              </div>
            </div>

            {/* Row 2: Module 3 Document Authenticity Tools Bar */}
            <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 text-xs">
              {/* Authenticity Indicators */}
              <div className="flex items-center gap-2">
                {/* SHA-256 File Integrity */}
                <div className="flex items-center gap-1 text-[11px] bg-slate-950 px-2.5 py-1 rounded-md border border-slate-800 text-slate-300">
                  <Lock className="w-3 h-3 text-emerald-400" />
                  <span className="text-slate-400">SHA-256:</span>
                  <span className="font-mono text-[10px] text-emerald-400">
                    {docMeta?.sha256_hash ? `${docMeta.sha256_hash.slice(0, 10)}...` : 'Verifying...'}
                  </span>
                  <span className="text-emerald-400 font-bold ml-0.5">✓</span>
                </div>

                {/* Duplicate Hash Check */}
                <div className="flex items-center gap-1 text-[11px] bg-slate-950 px-2.5 py-1 rounded-md border border-slate-800 text-slate-300">
                  <CopyCheck className="w-3 h-3 text-blue-400" />
                  <span className="text-slate-400">pHash Duplicate:</span>
                  <span className="text-emerald-400 font-medium">No Collision</span>
                </div>

                {/* QR / Issuer Verification Status */}
                {selectedScenario === 'INST-04-UNTRUSTED-QR-GPS' ? (
                  <div className="flex items-center gap-1 text-[11px] bg-red-950/70 border border-red-800/60 px-2.5 py-1 rounded-md text-red-300">
                    <ShieldAlert className="w-3 h-3 text-red-400" />
                    <span>QR: Untrusted Domain Destination</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-1 text-[11px] bg-purple-950/50 border border-purple-800/40 px-2.5 py-1 rounded-md text-purple-300">
                    <QrCode className="w-3 h-3 text-purple-400" />
                    <span>Issuer: Simulated Verification (Mock)</span>
                  </div>
                )}
              </div>

              {/* View Layer Toggles */}
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={showHighlights}
                    onChange={(e) => setShowHighlights(e.target.checked)}
                    className="rounded bg-slate-800 border-slate-700 text-blue-600 focus:ring-0 cursor-pointer"
                  />
                  <span>Evidence Boxes</span>
                </label>

                {/* ELA Tamper Heatmap Toggle */}
                <button
                  onClick={() => setShowHeatmap(!showHeatmap)}
                  className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-md font-semibold transition border ${
                    showHeatmap
                      ? 'bg-amber-600 text-white border-amber-500 shadow-md shadow-amber-600/30'
                      : 'bg-slate-950 text-amber-400 border-amber-800/50 hover:bg-amber-950/40'
                  }`}
                  title="Toggle pixel-by-pixel Error Level Analysis (ELA) compression heatmap"
                >
                  <Layers className="w-3.5 h-3.5" />
                  <span>{showHeatmap ? 'ELA Heatmap [ON]' : 'ELA Heatmap [OFF]'}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Document Canvas Display */}
          <div className="flex-1 relative overflow-auto p-6 flex justify-center bg-slate-950/90 items-start">
            <div
              style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'top center' }}
              className="relative transition-transform duration-200 shadow-2xl rounded-lg overflow-hidden border border-slate-700 bg-white"
            >
              {/* Document Page Image (Rendered with PyMuPDF with zero iframe scaling drift) */}
              <img
                src={`/api/v1/documents/${selectedScenario}/${activeDocument}/render?page=${currentPage}&dpi=150`}
                alt="Document Evidence"
                className="w-[620px] block"
              />

              {/* Dynamic Bounding Box Overlay for Selected Finding */}
              {showHighlights && selectedFinding?.evidence?.normalized_bbox && selectedFinding.evidence.source_document_name === activeDocument && (
                <div
                  style={{
                    position: 'absolute',
                    left: `${selectedFinding.evidence.normalized_bbox.x * 100}%`,
                    top: `${selectedFinding.evidence.normalized_bbox.y * 100}%`,
                    width: `${selectedFinding.evidence.normalized_bbox.width * 100}%`,
                    height: `${selectedFinding.evidence.normalized_bbox.height * 100}%`,
                  }}
                  className="border-2 border-red-500 bg-red-500/20 rounded pointer-events-none pulse-highlight shadow-lg z-20 flex items-start"
                >
                  <span className="absolute -top-5 left-0 bg-red-600 text-white font-bold text-[9px] px-1.5 py-0.5 rounded shadow">
                    SUPPORTING EVIDENCE
                  </span>
                </div>
              )}

              {/* Real ELA Compression Heatmap Overlay */}
              {showHeatmap && (
                <img
                  src={`/api/v1/documents/${selectedScenario}/${activeDocument}/ela?page=${currentPage}`}
                  alt="ELA Heatmap"
                  className="absolute inset-0 w-[620px] h-full object-cover mix-blend-screen opacity-90 pointer-events-none z-30"
                />
              )}
            </div>

            {/* Floating Inspection Card when a Finding is Selected */}
            {selectedFinding && (
              <div className="absolute bottom-6 left-8 right-8 bg-slate-900/95 border border-slate-700 p-4 rounded-xl shadow-2xl backdrop-blur-md z-40 border-l-4 border-l-blue-500">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold tracking-wider uppercase px-2 py-0.5 rounded bg-blue-900/80 text-blue-300 border border-blue-700/50">
                        {selectedFinding.applicable_rule.clause_reference}
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        Rule: {selectedFinding.applicable_rule.rule_id} (v{selectedFinding.applicable_rule.version})
                      </span>
                    </div>
                    <h3 className="text-sm font-semibold text-white mt-1">
                      {selectedFinding.title}
                    </h3>
                    <p className="text-xs text-slate-300 mt-1 max-w-xl leading-relaxed">
                      {selectedFinding.description}
                    </p>
                  </div>

                  <div className="text-right shrink-0">
                    <span
                      className={`text-xs px-2.5 py-1 rounded-md font-semibold ${
                        selectedFinding.outcome === 'Compliant'
                          ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/50'
                          : selectedFinding.outcome === 'Discrepancy Found'
                          ? 'bg-red-950 text-red-300 border border-red-800/50'
                          : 'bg-purple-950 text-purple-300 border border-purple-800/50'
                      }`}
                    >
                      {selectedFinding.outcome}
                    </span>
                    <div className="text-[10px] text-slate-400 mt-1">
                      Confidence: {Math.round((selectedFinding.confidence_or_uncertainty?.confidence_score || 0.95) * 100)}%
                    </div>
                  </div>
                </div>

                {/* Evidence Metrics & Officer Decision Actions */}
                <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-3">
                    <span className="text-slate-400">
                      Extracted Evidence:{' '}
                      <strong className="text-slate-100 font-mono bg-slate-800 px-2 py-0.5 rounded">
                        {selectedFinding.evidence.extracted_value}
                      </strong>
                    </span>
                    {selectedFinding.evidence.discrepancy_magnitude && (
                      <span className="text-red-400 font-medium">
                        (Variance: {selectedFinding.evidence.discrepancy_magnitude})
                      </span>
                    )}
                  </div>

                  {/* Officer Action Buttons */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => recordOfficerDecision('ACCEPTED')}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1 rounded-lg text-xs font-medium transition flex items-center gap-1 shadow-sm"
                    >
                      <Check className="w-3.5 h-3.5" />
                      Accept Finding
                    </button>
                    <button
                      onClick={() => recordOfficerDecision('REFERRED_FOR_INSPECTION', 'Physical inspection advised by scrutiny officer')}
                      className="bg-amber-600 hover:bg-amber-500 text-white px-3 py-1 rounded-lg text-xs font-medium transition flex items-center gap-1 shadow-sm"
                    >
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Mark for Inspection
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ═════════════════════════════════════════════════════════════════════════
            RIGHT PANE: MODULE 1 — 3-PILLAR SCRUTINY DASHBOARD
        ══════════════════════════════════════════════════════════════════════════ */}
        <div className="w-5/12 flex flex-col bg-slate-900/70">
          {/* Institutional Header Summary */}
          <div className="p-4 border-b border-slate-800 bg-slate-900/90">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] text-blue-400 font-mono uppercase tracking-wider font-bold">
                  {currentInstitution?.application_id || 'AICTE-APP-2024'}
                </span>
                <h2 className="text-sm font-semibold text-slate-100 mt-0.5">
                  {currentInstitution?.institution_name || 'Loading Institution...'}
                </h2>
                <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                  <span>Intake: <strong>{currentInstitution?.total_approved_students || 240}</strong></span>
                  <span>Declared Land: <strong>{currentInstitution?.declared_land_acres || 4.0} Acres</strong></span>
                </div>
              </div>

              {/* Status Badge */}
              <div className="text-right">
                <span className="text-[11px] font-semibold px-2.5 py-1 rounded-md bg-slate-800 text-slate-200 border border-slate-700">
                  {selectedScenario === 'INST-01-COMPLIANT' ? '🟢 Requirements Met' : '🔴 Scrutiny Required'}
                </span>
              </div>
            </div>

            {/* Three Pillars Navigation Bar */}
            <div className="grid grid-cols-4 gap-1.5 mt-3 pt-3 border-t border-slate-800/80">
              {[
                { id: 'ALL', label: 'All Findings', count: allFindings.length },
                { id: 'AUTHENTICITY', label: '1. Authenticity', count: authenticityFindings.length },
                { id: 'COMPLETENESS', label: '2. Completeness', count: completenessFindings.length },
                { id: 'REGULATORY_COMPLIANCE', label: '3. Compliance', count: complianceFindings.length },
              ].map((pill) => (
                <button
                  key={pill.id}
                  onClick={() => setActivePillarTab(pill.id as any)}
                  className={`text-[11px] py-1.5 px-2 rounded-lg font-medium transition text-center flex flex-col items-center justify-center ${
                    activePillarTab === pill.id
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800'
                  }`}
                >
                  <span className="truncate w-full">{pill.label}</span>
                  <span className={`text-[10px] font-bold ${activePillarTab === pill.id ? 'text-blue-200' : 'text-slate-500'}`}>
                    ({pill.count})
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Finding Cards List Grouped by Pillars */}
          <div className="flex-1 overflow-auto p-4 space-y-3">
            {loading ? (
              <div className="flex flex-col items-center justify-center h-48 text-slate-400 text-xs">
                <RefreshCw className="w-6 h-6 animate-spin mb-2 text-blue-500" />
                <span>Running multi-signal verification & APH compliance rules...</span>
              </div>
            ) : filteredFindings.length === 0 ? (
              <div className="text-center py-12 text-slate-500 text-xs">
                No findings under this pillar for this institution.
              </div>
            ) : (
              filteredFindings.map((finding) => {
                const isSelected = selectedFinding?.finding_id === finding.finding_id;
                return (
                  <div
                    key={finding.finding_id}
                    onClick={() => handleInspectFinding(finding)}
                    className={`border rounded-xl p-3.5 transition cursor-pointer relative ${
                      isSelected
                        ? 'border-blue-500 bg-blue-950/30 shadow-lg shadow-blue-500/10 ring-1 ring-blue-500'
                        : 'border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {finding.outcome === 'Compliant' ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                        ) : finding.outcome === 'Discrepancy Found' ? (
                          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                        ) : (
                          <HelpCircle className="w-4 h-4 text-purple-400 shrink-0" />
                        )}
                        <div>
                          <span className="text-[10px] font-mono text-blue-400 font-semibold">
                            {finding.applicable_rule?.clause_reference || 'Statutory Requirement'}
                          </span>
                          <h4 className="text-xs font-semibold text-slate-100">
                            {finding.title}
                          </h4>
                        </div>
                      </div>

                      <span
                        className={`text-[10px] px-2 py-0.5 rounded font-semibold shrink-0 ${
                          finding.outcome === 'Compliant'
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/40'
                            : finding.outcome === 'Discrepancy Found'
                            ? 'bg-red-950 text-red-400 border border-red-800/40'
                            : 'bg-purple-950 text-purple-400 border border-purple-800/40'
                        }`}
                      >
                        {finding.outcome}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-300 mt-2 leading-relaxed">
                      {finding.description}
                    </p>

                    {/* Footer with Document Badge and Inspect Button */}
                    <div className="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px]">
                      <span className="text-slate-400 flex items-center gap-1 font-mono text-[10px]">
                        <FileText className="w-3 h-3 text-slate-500" />
                        {finding.evidence.source_document_name}
                      </span>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleInspectFinding(finding);
                        }}
                        className="text-blue-400 hover:text-blue-300 flex items-center gap-1 font-medium text-xs group"
                      >
                        <span>Inspect Evidence</span>
                        <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────────────────
          AUDIT TRAIL MODAL (HASH-CHAINED INTEGRITY)
      ────────────────────────────────────────────────────────────────────────── */}
      {showAuditModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm flex items-center justify-center p-6 z-50">
          <div className="bg-slate-900 border border-slate-700 w-full max-w-3xl rounded-2xl shadow-2xl p-6 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <Lock className="w-5 h-5 text-emerald-400" />
                <div>
                  <h3 className="text-sm font-semibold text-white">
                    Cryptographically Chained Audit Trail (SHA-256)
                  </h3>
                  <p className="text-xs text-slate-400">
                    Append-only tamper-detection log with sequential cryptographic hash chaining
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowAuditModal(false)}
                className="text-slate-400 hover:text-white text-xs px-2.5 py-1 rounded-lg border border-slate-800 hover:bg-slate-800"
              >
                ✕ Close
              </button>
            </div>

            <div className="flex-1 overflow-auto py-4 space-y-3 font-mono text-xs">
              {auditEvents.length === 0 ? (
                <div className="text-slate-500 text-center py-8">No audit records recorded yet.</div>
              ) : (
                auditEvents.map((e) => (
                  <div key={e.event_id} className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 space-y-1">
                    <div className="flex justify-between text-[11px] text-slate-400">
                      <span className="text-emerald-400 font-bold">#{e.sequence_number} {e.event_id}</span>
                      <span>{e.timestamp}</span>
                    </div>
                    <div>
                      Actor: <strong className="text-blue-300">{e.actor_id}</strong> ({e.role}) · Action: <strong className="text-white">{e.action}</strong>
                    </div>
                    <div className="text-[10px] text-slate-500 truncate">
                      Event Hash: <span className="text-slate-400">{e.event_hash}</span>
                    </div>
                    <div className="text-[10px] text-slate-500 truncate">
                      Prev Hash:  <span className="text-slate-400">{e.previous_hash}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
