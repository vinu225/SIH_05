import React, { useState, useEffect } from 'react';
import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  ShieldCheck,
  Eye,
  ZoomIn,
  Search,
  Lock,
  RefreshCw,
  Sliders,
  ExternalLink,
  ChevronRight,
  UserCheck,
  Building2,
  GraduationCap,
  MapPin,
  Flame,
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

export default function App() {
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>('INST-01-COMPLIANT');
  const [evaluationData, setEvaluationData] = useState<any>(null);
  const [activeDocument, setActiveDocument] = useState<string>('Fire_Safety_NOC.pdf');
  const [selectedFinding, setSelectedFinding] = useState<FindingRecord | null>(null);
  const [showHeatmap, setShowHeatmap] = useState<boolean>(false);
  const [showHighlights, setShowHighlights] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<string>('ALL');
  const [loading, setLoading] = useState<boolean>(false);
  const [auditEvents, setAuditEvents] = useState<any[]>([]);
  const [showAuditModal, setShowAuditModal] = useState<boolean>(false);

  // Fetch scenarios on load
  useEffect(() => {
    fetch('/api/v1/scenarios')
      .then((res) => res.json())
      .then((data) => {
        if (data.scenarios && data.scenarios.length > 0) {
          setScenarios(data.scenarios);
          loadScenario(data.scenarios[0].application_id.replace('APP-2024-', ''));
        }
      })
      .catch(() => {
        // Fallback demo scenarios if backend not yet running
        const mockList = [
          { application_id: 'APP-2024-INST-01-COMPLIANT', institution_name: 'K.J. Somaiya Institute of Engineering & Technology' },
          { application_id: 'APP-2024-INST-02-DATE-ALTERED', institution_name: 'Vidyavardhini Technical Institute of Technology' },
          { application_id: 'APP-2024-INST-03-LAND-CADRE-DISCREPANCY', institution_name: 'Apex National Institute of Management & Science' },
          { application_id: 'APP-2024-INST-04-UNTRUSTED-QR-GPS', institution_name: 'Global Horizon College of Engineering' },
        ];
        setScenarios(mockList);
        loadScenario('INST-01-COMPLIANT');
      });
  }, []);

  const loadScenario = (scenarioId: string) => {
    setLoading(true);
    setSelectedScenario(scenarioId);
    setSelectedFinding(null);
    setShowHeatmap(false);

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
    }
  };

  const recordOfficerDecision = (decision: string) => {
    if (!selectedFinding) return;
    fetch('/api/v1/officer/decision', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        finding_id: selectedFinding.finding_id,
        decision: decision,
        officer_id: 'OFFICER-REG-9812',
        reason: 'Officer reviewed via Split-Screen Scrutiny Cockpit',
      }),
    })
      .then(() => {
        alert(`Action recorded: Finding ${selectedFinding.finding_id} marked as ${decision}`);
        // Refresh scenario
        loadScenario(selectedScenario);
      })
      .catch(() => alert('Recorded decision in local session.'));
  };

  const fetchAuditTrail = () => {
    fetch('/api/v1/audit/trail')
      .then((res) => res.json())
      .then((data) => {
        setAuditEvents(data.events || []);
        setShowAuditModal(true);
      });
  };

  const filteredFindings: FindingRecord[] = evaluationData?.findings
    ? evaluationData.findings.filter((f: FindingRecord) => {
        if (activeTab === 'ALL') return true;
        return f.assessment_pillar === activeTab;
      })
    : [];

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      {/* Top AICTE Navigation Header */}
      <header className="h-16 border-b border-slate-800 bg-slate-900/90 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/20">
            AICTE
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-wide text-slate-100 flex items-center gap-2">
              Regulation Bureau · Scrutiny Decision-Support Platform
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-900/60 text-blue-300 border border-blue-700/50">
                APH 2024–2027
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Extension of Approval (EoA) & Institutional Regulatory Scrutiny
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          {/* Scenario Selector Dropdown */}
          <div className="flex items-center gap-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
            <span className="text-xs text-slate-400">Test Case:</span>
            <select
              value={selectedScenario}
              onChange={(e) => loadScenario(e.target.value)}
              className="bg-transparent text-xs text-slate-200 font-medium focus:outline-none cursor-pointer"
            >
              {scenarios.map((s) => {
                const id = s.application_id.replace('APP-2024-', '');
                return (
                  <option key={id} value={id} className="bg-slate-900 text-slate-100">
                    {id} — {s.institution_name.slice(0, 32)}...
                  </option>
                );
              })}
            </select>
          </div>

          <button
            onClick={fetchAuditTrail}
            className="flex items-center gap-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700 transition"
          >
            <Lock className="w-3.5 h-3.5 text-emerald-400" />
            <span>Audit Trail (SHA-256)</span>
          </button>
        </div>
      </header>

      {/* Main Split-Screen Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT PANE: Document Viewer & Highlight Canvas */}
        <div className="w-7/12 border-r border-slate-800 flex flex-col bg-slate-900/40">
          {/* Document Tabs & Canvas Layer Controls */}
          <div className="h-12 border-b border-slate-800 px-4 flex items-center justify-between bg-slate-900/60">
            <div className="flex items-center gap-2">
              {['Fire_Safety_NOC.pdf', 'Land_Title_Deed.pdf', 'Faculty_Portfolio.pdf'].map((docName) => (
                <button
                  key={docName}
                  onClick={() => setActiveDocument(docName)}
                  className={`text-xs px-3 py-1.5 rounded-md font-medium transition flex items-center gap-1.5 ${
                    activeDocument === docName
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  {docName.replace('.pdf', '')}
                </button>
              ))}
            </div>

            {/* Layer Toggles */}
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showHighlights}
                  onChange={(e) => setShowHighlights(e.target.checked)}
                  className="rounded bg-slate-800 border-slate-700 text-blue-500 focus:ring-0 cursor-pointer"
                />
                <span>OCR Highlights</span>
              </label>

              <label className="flex items-center gap-1.5 text-xs text-amber-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showHeatmap}
                  onChange={(e) => setShowHeatmap(e.target.checked)}
                  className="rounded bg-slate-800 border-slate-700 text-amber-500 focus:ring-0 cursor-pointer"
                />
                <span>ELA Tamper Heatmap</span>
              </label>
            </div>
          </div>

          {/* Document Display Canvas */}
          <div className="flex-1 relative overflow-auto p-6 flex justify-center bg-slate-950/80">
            <div className="relative w-full max-w-2xl bg-white rounded shadow-2xl overflow-hidden min-h-[750px] border border-slate-700">
              {/* Embedded Document Frame */}
              <iframe
                src={`/api/v1/documents/${selectedScenario}/${activeDocument}#toolbar=0`}
                className="w-full h-full min-h-[750px] border-0"
                title="Document Preview"
              />

              {/* Dynamic Coordinate Highlight Box */}
              {showHighlights && selectedFinding?.evidence?.normalized_bbox && (
                <div
                  style={{
                    position: 'absolute',
                    left: `${selectedFinding.evidence.normalized_bbox.x * 100}%`,
                    top: `${selectedFinding.evidence.normalized_bbox.y * 100}%`,
                    width: `${selectedFinding.evidence.normalized_bbox.width * 100}%`,
                    height: `${selectedFinding.evidence.normalized_bbox.height * 100}%`,
                  }}
                  className="border-2 border-red-500 bg-red-500/20 rounded pointer-events-none pulse-highlight shadow-lg z-20"
                >
                  <div className="absolute -top-6 left-0 bg-red-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded shadow">
                    FLAGGED EVIDENCE
                  </div>
                </div>
              )}

              {/* Simulated ELA Forensic Heatmap Overlay */}
              {showHeatmap && (
                <div className="absolute inset-0 bg-red-950/20 backdrop-blur-[0.5px] pointer-events-none flex items-center justify-center z-30">
                  <div className="border border-red-500/40 bg-red-900/30 text-red-200 text-xs px-4 py-2 rounded-lg font-mono">
                    [ELA COMPRESSION HEATMAP ACTIVE · PIXEL DISPARITY SIGNAL OVERLAY]
                  </div>
                </div>
              )}
            </div>

            {/* On-Canvas Floating Callout Card when finding is inspected */}
            {selectedFinding && (
              <div className="absolute bottom-6 left-8 right-8 bg-slate-900/95 border border-slate-700 p-4 rounded-xl shadow-2xl backdrop-blur-md z-40 animate-fade-in">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-bold tracking-wider uppercase px-2 py-0.5 rounded bg-blue-900/80 text-blue-300 border border-blue-700/50">
                      {selectedFinding.applicable_rule.clause_reference}
                    </span>
                    <h3 className="text-sm font-semibold text-white mt-1">
                      {selectedFinding.title}
                    </h3>
                    <p className="text-xs text-slate-300 mt-1 max-w-xl">
                      {selectedFinding.description}
                    </p>
                  </div>
                  <div className="text-right">
                    <span
                      className={`text-xs px-2.5 py-1 rounded-md font-semibold ${
                        selectedFinding.outcome === 'Compliant'
                          ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-700/50'
                          : selectedFinding.outcome === 'Discrepancy Found'
                          ? 'bg-red-900/60 text-red-300 border border-red-700/50'
                          : 'bg-purple-900/60 text-purple-300 border border-purple-700/50'
                      }`}
                    >
                      {selectedFinding.outcome}
                    </span>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
                  <span className="text-slate-400">
                    Evidence Value:{' '}
                    <strong className="text-slate-100">
                      {selectedFinding.evidence.extracted_value}
                    </strong>
                  </span>

                  <div className="flex gap-2">
                    <button
                      onClick={() => recordOfficerDecision('ACCEPTED')}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1 rounded text-xs font-medium transition"
                    >
                      Accept Finding
                    </button>
                    <button
                      onClick={() => recordOfficerDecision('REFERRED_FOR_INSPECTION')}
                      className="bg-amber-600 hover:bg-amber-500 text-white px-3 py-1 rounded text-xs font-medium transition"
                    >
                      Mark for Inspection
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT PANE: Scrutiny Audit Cards & Decision Panel */}
        <div className="w-5/12 flex flex-col bg-slate-900/80">
          {/* Header Summary */}
          <div className="p-4 border-b border-slate-800 bg-slate-900/90">
            <h2 className="text-sm font-semibold text-slate-200">
              Scrutiny Checklist & Decision-Support Findings
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Preliminary validation against AICTE APH 2024–27 regulations
            </p>

            {/* 3-Pillar Filter Tabs */}
            <div className="flex items-center gap-1.5 mt-3">
              {[
                { id: 'ALL', label: 'All Findings' },
                { id: 'REGULATORY_COMPLIANCE', label: 'Compliance' },
                { id: 'AUTHENTICITY', label: 'Authenticity' },
                { id: 'COMPLETENESS', label: 'Completeness' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`text-[11px] px-2.5 py-1 rounded-md font-medium transition ${
                    activeTab === tab.id
                      ? 'bg-slate-700 text-white'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Finding Cards List */}
          <div className="flex-1 overflow-auto p-4 space-y-3">
            {loading ? (
              <div className="flex flex-col items-center justify-center h-48 text-slate-400 text-xs">
                <RefreshCw className="w-5 h-5 animate-spin mb-2 text-blue-500" />
                Evaluating APH rules and documents...
              </div>
            ) : filteredFindings.length === 0 ? (
              <div className="text-center py-12 text-slate-400 text-xs">
                No findings under this category.
              </div>
            ) : (
              filteredFindings.map((finding) => {
                const isSelected = selectedFinding?.finding_id === finding.finding_id;
                return (
                  <div
                    key={finding.finding_id}
                    className={`border rounded-xl p-3.5 transition cursor-pointer ${
                      isSelected
                        ? 'border-blue-500 bg-blue-950/20 shadow-lg'
                        : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                    }`}
                    onClick={() => handleInspectFinding(finding)}
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
                        <h4 className="text-xs font-semibold text-slate-100">
                          {finding.title}
                        </h4>
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

                    <div className="mt-2.5 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-400">
                      <span>Doc: {finding.evidence.source_document_name}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleInspectFinding(finding);
                        }}
                        className="text-blue-400 hover:text-blue-300 flex items-center gap-1 font-medium"
                      >
                        <ZoomIn className="w-3 h-3" />
                        <span>Inspect in Document</span>
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Audit Trail Modal */}
      {showAuditModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-6 z-50">
          <div className="bg-slate-900 border border-slate-700 w-full max-w-3xl rounded-xl shadow-2xl p-6 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Lock className="w-5 h-5 text-emerald-400" />
                <h3 className="text-sm font-semibold text-white">
                  Cryptographically Chained Audit Trail (SHA-256)
                </h3>
              </div>
              <button
                onClick={() => setShowAuditModal(false)}
                className="text-slate-400 hover:text-white text-xs px-2 py-1"
              >
                ✕ Close
              </button>
            </div>

            <div className="flex-1 overflow-auto py-4 space-y-3 font-mono text-xs">
              {auditEvents.length === 0 ? (
                <div className="text-slate-500 text-center py-6">No audit records found.</div>
              ) : (
                auditEvents.map((e) => (
                  <div key={e.event_id} className="p-3 rounded bg-slate-950 border border-slate-800">
                    <div className="flex justify-between text-slate-400 text-[11px]">
                      <span className="text-emerald-400 font-bold">#{e.sequence_number} {e.event_id}</span>
                      <span>{e.timestamp}</span>
                    </div>
                    <div className="mt-1 text-slate-200">
                      Actor: <span className="text-blue-300">{e.actor_id} ({e.role})</span> · Action: <strong>{e.action}</strong>
                    </div>
                    <div className="text-[10px] text-slate-500 truncate mt-1">
                      Event Hash: {e.event_hash}
                    </div>
                    <div className="text-[10px] text-slate-500 truncate">
                      Prev Hash: {e.previous_hash}
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
