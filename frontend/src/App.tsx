import React, { useState, useEffect } from 'react';
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
  ChevronLeft,
  ChevronDown,
  Info,
  Check,
  X,
  FileCheck,
  SlidersHorizontal,
  Search,
  Calendar,
  Download,
  Lightbulb,
  Clock,
  ArrowRight,
  ExternalLink,
  LayoutDashboard,
  Plus,
  Filter,
  CheckSquare,
  Square,
  Sparkles,
  BookOpen,
  UploadCloud,
  Upload,
  FileUp,
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
  const [currentView, setCurrentView] = useState<'DOCUMENT_REVIEW' | 'AUDIT_TIMELINE' | 'APH_RULES'>('DOCUMENT_REVIEW');
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
  const [aphRules, setAphRules] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [timelineFilterStatus, setTimelineFilterStatus] = useState<string>('ALL');

  // Upload modal state
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadDocType, setUploadDocType] = useState<string>('Fire_Safety_NOC');
  const [uploadScenarioTarget, setUploadScenarioTarget] = useState<string>('CURRENT');
  const [customScenarioId, setCustomScenarioId] = useState<string>('');
  const [customInstitutionName, setCustomInstitutionName] = useState<string>('');
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [uploadedDocsList, setUploadedDocsList] = useState<string[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Load scenarios & rules on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const queryScenario = params.get('scenario');

    fetch('/api/v1/scenarios')
      .then((res) => res.json())
      .then((data) => {
        if (data.scenarios && data.scenarios.length > 0) {
          setScenarios(data.scenarios);
          if (queryScenario) {
            loadScenario(queryScenario);
          } else {
            const initialId = data.scenarios[0].application_id.replace('APP-2024-', '');
            loadScenario(initialId);
          }
        }
      })
      .catch((err) => {
        console.error('Failed to load scenarios:', err);
        setLoadError('Failed to load institution scenarios from backend.');
      });

    fetch('/api/v1/rules')
      .then((res) => res.json())
      .then((data) => setAphRules(data.rules || []))
      .catch((err) => console.error('Failed to load APH rules:', err));

    fetchAuditTrail();
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
    setLoadError(null);
    setSelectedScenario(scenarioId);
    setSelectedFinding(null);
    setShowHeatmap(false);
    setCurrentPage(1);

    try {
      const url = new URL(window.location.href);
      if (url.searchParams.get('scenario') !== scenarioId) {
        url.searchParams.set('scenario', scenarioId);
        window.history.replaceState({}, '', url.toString());
      }
    } catch {}

    fetch(`/api/v1/evaluate/${scenarioId}`, { method: 'POST' })
      .then(async (res) => {
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Institution scenario '${scenarioId}' not found (HTTP ${res.status})`);
        }
        return res.json();
      })
      .then((data) => {
        setEvaluationData(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoadError(err.message || 'Error evaluating scenario');
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
        reason: reason || 'Verified through AICTE Scrutiny Platform',
      }),
    })
      .then(() => {
        loadScenario(selectedScenario);
        fetchAuditTrail();
      })
      .catch((err) => console.error('Failed to record decision:', err));
  };

  const fetchAuditTrail = () => {
    fetch('/api/v1/audit/trail')
      .then((res) => res.json())
      .then((data) => {
        setAuditEvents(data.events || []);
      })
      .catch((err) => console.error('Failed to load audit trail:', err));
  };

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError('Please select a PDF, PNG, or JPEG file to upload.');
      return;
    }
    setUploading(true);
    setUploadError(null);
    setUploadResult(null);

    const targetScenario =
      uploadScenarioTarget === 'NEW'
        ? (customScenarioId.trim().toUpperCase() || `INST-${Date.now().toString().slice(-4)}`)
        : selectedScenario;

    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('scenario_id', targetScenario);
    formData.append('document_type', uploadDocType);
    if (uploadScenarioTarget === 'NEW' && customInstitutionName) {
      formData.append('institution_name', customInstitutionName);
    }

    try {
      const res = await fetch('/api/v1/documents/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Upload failed');
      }

      setUploadResult(data);
      setUploading(false);

      // Track uploaded document name
      if (!uploadedDocsList.includes(data.filename)) {
        setUploadedDocsList((prev) => [...prev, data.filename]);
      }

      // Refresh scenarios list & load scenario
      fetch('/api/v1/scenarios')
        .then((r) => r.json())
        .then((sData) => {
          if (sData.scenarios) setScenarios(sData.scenarios);
        });

      loadScenario(targetScenario);
      setActiveDocument(data.filename);
      fetchAuditTrail();
    } catch (err: any) {
      setUploadError(err.message || 'An error occurred during upload.');
      setUploading(false);
    }
  };

  const allFindings: FindingRecord[] = evaluationData?.findings || [];
  const filteredFindings = allFindings.filter((f) => {
    if (activePillarTab === 'ALL') return true;
    return f.assessment_pillar === activePillarTab;
  });

  const authenticityFindings = allFindings.filter((f) => f.assessment_pillar === 'AUTHENTICITY');
  const completenessFindings = allFindings.filter((f) => f.assessment_pillar === 'COMPLETENESS');
  const complianceFindings = allFindings.filter((f) => f.assessment_pillar === 'REGULATORY_COMPLIANCE');

  const discrepancyCount = allFindings.filter((f) => f.outcome !== 'Compliant').length;
  const currentInstitution = evaluationData?.application_metadata;

  return (
    <div className="min-h-screen flex bg-[#f4f6f9] text-slate-800 font-sans antialiased selection:bg-blue-600 selection:text-white">
      {/* ─────────────────────────────────────────────────────────────────────────
          SLIM LEFT NAVIGATION RAIL (Inspired by Reference Image 2)
      ────────────────────────────────────────────────────────────────────────── */}
      <aside className="w-16 bg-white border-r border-slate-200/80 flex flex-col items-center py-4 justify-between shrink-0 shadow-sm z-30">
        <div className="flex flex-col items-center gap-6 w-full">
          {/* Logo Brand Mark */}
          <div className="h-10 w-10 rounded-2xl bg-gradient-to-tr from-sky-400 to-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20 font-bold text-sm tracking-wider cursor-pointer">
            <span className="text-white drop-shadow-sm font-black">AI</span>
          </div>

          {/* Navigation Icons Rail */}
          <nav className="flex flex-col items-center gap-2 w-full px-2">
            <button
              onClick={() => setCurrentView('DOCUMENT_REVIEW')}
              className={`w-11 h-11 rounded-xl flex items-center justify-center transition-all ${
                currentView === 'DOCUMENT_REVIEW'
                  ? 'bg-sky-50 text-sky-600 shadow-sm border border-sky-100 font-semibold'
                  : 'text-slate-400 hover:text-slate-700 hover:bg-slate-100/80'
              }`}
              title="Document Review & Evidence Split-Screen"
            >
              <FileText className="w-5 h-5" />
            </button>

            <button
              onClick={() => setCurrentView('AUDIT_TIMELINE')}
              className={`w-11 h-11 rounded-xl flex items-center justify-center transition-all ${
                currentView === 'AUDIT_TIMELINE'
                  ? 'bg-sky-50 text-sky-600 shadow-sm border border-sky-100 font-semibold'
                  : 'text-slate-400 hover:text-slate-700 hover:bg-slate-100/80'
              }`}
              title="Audit Trail Timeline & Filter Controls"
            >
              <Clock className="w-5 h-5" />
            </button>

            <button
              onClick={() => setCurrentView('APH_RULES')}
              className={`w-11 h-11 rounded-xl flex items-center justify-center transition-all ${
                currentView === 'APH_RULES'
                  ? 'bg-sky-50 text-sky-600 shadow-sm border border-sky-100 font-semibold'
                  : 'text-slate-400 hover:text-slate-700 hover:bg-slate-100/80'
              }`}
              title="AICTE APH 2024–2027 Handbook Rules"
            >
              <ShieldCheck className="w-5 h-5" />
            </button>

            <div className="w-6 h-[1px] bg-slate-200 my-1"></div>

            <button
              onClick={() => {
                setActivePillarTab('AUTHENTICITY');
                setCurrentView('DOCUMENT_REVIEW');
              }}
              className="w-11 h-11 rounded-xl flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100/80 transition"
              title="Authenticity Verification"
            >
              <Lock className="w-4 h-4" />
            </button>

            <button
              onClick={() => {
                setActivePillarTab('REGULATORY_COMPLIANCE');
                setCurrentView('DOCUMENT_REVIEW');
              }}
              className="w-11 h-11 rounded-xl flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100/80 transition"
              title="Statutory Ratios & Compliance"
            >
              <Scale className="w-4 h-4" />
            </button>
          </nav>
        </div>

        {/* Bottom Rail Actions */}
        <div className="flex flex-col items-center gap-3 w-full px-2">
          <button
            onClick={() => loadScenario(selectedScenario)}
            className="w-10 h-10 rounded-xl flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
            title="Refresh Evaluation"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-blue-600' : ''}`} />
          </button>
          <div
            onClick={() => {
              setUploadResult(null);
              setUploadError(null);
              setUploadFile(null);
              setShowUploadModal(true);
            }}
            className="w-9 h-9 rounded-xl bg-sky-500 hover:bg-sky-600 text-white flex items-center justify-center shadow-md shadow-sky-500/20 cursor-pointer transition"
            title="Upload Evidence Document"
          >
            <Plus className="w-5 h-5" />
          </div>
        </div>
      </aside>

      {/* ─────────────────────────────────────────────────────────────────────────
          MAIN APPLICATION VIEW CONTAINER
      ────────────────────────────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header / Breadcrumbs & Tab Bar (Image 1 & 2 Header) */}
        <header className="bg-white border-b border-slate-200/90 px-6 py-2.5 flex flex-col gap-2 shrink-0 shadow-xs">
          <div className="flex items-center justify-between">
            {/* Breadcrumb Path */}
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <LayoutDashboard className="w-3.5 h-3.5 text-slate-400" />
              <ChevronRight className="w-3 h-3 text-slate-300" />
              <span className="font-medium text-slate-600">AICTE Applications</span>
              <ChevronRight className="w-3 h-3 text-slate-300" />
              <span className="font-semibold text-slate-800">
                {currentInstitution?.application_id || 'APP-2024-INST'}
              </span>
              <span className="ml-2 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-sky-50 text-sky-700 border border-sky-200">
                APH 2024–2027
              </span>
            </div>

            {/* Scenario Selector, Upload Action & Status Indicator */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  setUploadResult(null);
                  setUploadError(null);
                  setUploadFile(null);
                  setShowUploadModal(true);
                }}
                className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold shadow-xs transition"
                title="Ingest new statutory document"
              >
                <UploadCloud className="w-3.5 h-3.5" />
                <span>Upload Evidence</span>
              </button>

              <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 px-3 py-1 rounded-lg text-xs">
                <span className="text-slate-500 font-medium">Test Scenario:</span>
                <select
                  value={selectedScenario}
                  onChange={(e) => loadScenario(e.target.value)}
                  className="bg-transparent text-slate-800 font-semibold focus:outline-none cursor-pointer"
                >
                  {scenarios.map((s) => {
                    const id = s.application_id.replace('APP-2024-', '');
                    return (
                      <option key={id} value={id}>
                        {id}: {s.institution_name.slice(0, 32)}...
                      </option>
                    );
                  })}
                </select>
              </div>

              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-semibold">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Decision-Support Mode</span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs (Dashboard, Projects, Compliance, Reports) matching Image 1 */}
          <div className="flex items-center justify-between border-t border-slate-100 pt-2">
            <div className="flex items-center gap-6 text-xs font-semibold">
              <button
                onClick={() => setCurrentView('DOCUMENT_REVIEW')}
                className={`pb-1.5 relative transition-colors ${
                  currentView === 'DOCUMENT_REVIEW'
                    ? 'text-sky-600 font-bold'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Document Review
                {currentView === 'DOCUMENT_REVIEW' && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-sky-500 rounded-full" />
                )}
              </button>

              <button
                onClick={() => setCurrentView('AUDIT_TIMELINE')}
                className={`pb-1.5 relative transition-colors flex items-center gap-1.5 ${
                  currentView === 'AUDIT_TIMELINE'
                    ? 'text-sky-600 font-bold'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <span>Audit Trail Timeline</span>
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-100 text-slate-600 border border-slate-200">
                  {auditEvents.length}
                </span>
                {currentView === 'AUDIT_TIMELINE' && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-sky-500 rounded-full" />
                )}
              </button>

              <button
                onClick={() => setCurrentView('APH_RULES')}
                className={`pb-1.5 relative transition-colors ${
                  currentView === 'APH_RULES'
                    ? 'text-sky-600 font-bold'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Compliance Standards & Rules
                {currentView === 'APH_RULES' && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-sky-500 rounded-full" />
                )}
              </button>
            </div>

            {/* Non-prejudicial statutory notice */}
            <div className="flex items-center gap-1.5 text-[11px] text-amber-700 bg-amber-50 px-2.5 py-0.5 rounded-md border border-amber-200/80">
              <Info className="w-3 h-3 text-amber-600 shrink-0" />
              <span>Advisory AI Screen: Non-prejudicial assistance for Scrutiny Officers</span>
            </div>
          </div>
        </header>

        {/* ─────────────────────────────────────────────────────────────────────────
            ERROR STATE (Scenario Not Found / Network Failure)
        ────────────────────────────────────────────────────────────────────────── */}
        {loadError && (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="bg-white border border-rose-200 rounded-3xl p-8 max-w-lg w-full text-center shadow-lg shadow-rose-500/5">
              <div className="w-14 h-14 rounded-2xl bg-rose-50 border border-rose-100 flex items-center justify-center text-rose-500 mx-auto mb-4">
                <AlertTriangle className="w-7 h-7" />
              </div>
              <h2 className="text-lg font-bold text-slate-800">Institution Package Not Found</h2>
              <p className="text-xs text-slate-500 mt-2 mb-6 leading-relaxed">
                {loadError}
              </p>
              <div className="flex items-center justify-center gap-3">
                <button
                  onClick={() => loadScenario('INST-01-COMPLIANT')}
                  className="px-4 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold shadow-sm transition"
                >
                  Load Baseline Institution
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ─────────────────────────────────────────────────────────────────────────
            VIEW 1: DOCUMENT REVIEW SPLIT SCREEN (Inspired by Reference Image 2)
        ────────────────────────────────────────────────────────────────────────── */}
        {!loadError && currentView === 'DOCUMENT_REVIEW' && (
          <div className="flex-1 flex overflow-hidden">
            {/* ═══════════════════════════════════════════════════════════════════════
                LEFT SUB-PANEL: AI SUBMISSION READINESS & DECLARATIONS CHECKLIST
            ════════════════════════════════════════════════════════════════════════ */}
            <div className="w-64 bg-white border-r border-slate-200/90 flex flex-col p-4 shrink-0 overflow-y-auto">
              <div className="pb-3 border-b border-slate-100">
                <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
                  Scrutiny Application
                </span>
                <h3 className="text-xs font-bold text-slate-800 truncate mt-0.5" title={currentInstitution?.institution_name}>
                  {currentInstitution?.institution_name || 'Loading Institution...'}
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Type: {currentInstitution?.institution_category || 'UG Technical'} · Intake: {currentInstitution?.total_approved_students || 240}
                </p>
              </div>

              {/* AI Submission Readiness Card (Exact Image 2 Widget) */}
              <div className="mt-4 p-3 bg-slate-50/80 rounded-xl border border-slate-200/70">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-slate-700">AI Submission Readiness</span>
                  <Sparkles className="w-3.5 h-3.5 text-sky-500" />
                </div>
                <div className="grid grid-cols-2 gap-2 text-center">
                  <div className="bg-white p-2 rounded-lg border border-slate-200 shadow-2xs">
                    <div className="flex items-center justify-center gap-1 text-[11px] text-emerald-600 font-medium">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      Uploaded
                    </div>
                    <div className="text-base font-extrabold text-slate-800 mt-0.5">3</div>
                  </div>
                  <div className="bg-white p-2 rounded-lg border border-slate-200 shadow-2xs">
                    <div className="flex items-center justify-center gap-1 text-[11px] text-amber-600 font-medium">
                      <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                      Flags
                    </div>
                    <div className="text-base font-extrabold text-slate-800 mt-0.5">{discrepancyCount}</div>
                  </div>
                </div>
              </div>

              {/* Application & Declarations Checklist (Exact Image 2 Section) */}
              <div className="mt-4 flex-1">
                <div className="flex items-center justify-between text-xs font-bold text-slate-700 mb-2">
                  <span>Application & Declarations</span>
                  <button
                    onClick={() => {
                      setUploadResult(null);
                      setUploadError(null);
                      setUploadFile(null);
                      setShowUploadModal(true);
                    }}
                    className="text-[10px] text-sky-600 hover:text-sky-800 font-bold flex items-center gap-0.5 bg-sky-50 px-1.5 py-0.5 rounded border border-sky-200 transition hover:bg-sky-100"
                    title="Upload new document evidence"
                  >
                    <Plus className="w-3 h-3" />
                    <span>Upload</span>
                  </button>
                </div>

                <div className="space-y-1.5">
                  {[
                    {
                      file: 'Fire_Safety_NOC.pdf',
                      label: 'Fire Safety Certificate',
                      icon: Flame,
                      pages: 1,
                      status: selectedScenario === 'INST-02-DATE-ALTERED' ? 'flagged' : 'ok',
                      subtext: selectedScenario === 'INST-02-DATE-ALTERED' ? 'ELA compression anomaly' : 'Valid statutory period',
                    },
                    {
                      file: 'Land_Title_Deed.pdf',
                      label: 'Land Title Deed',
                      icon: Building2,
                      pages: 1,
                      status: selectedScenario === 'INST-03-LAND-CADRE-DISCREPANCY' ? 'flagged' : 'ok',
                      subtext: selectedScenario === 'INST-03-LAND-CADRE-DISCREPANCY' ? 'FSI/FAR Discrepancy' : 'FAR norms verified',
                    },
                    {
                      file: 'Faculty_Portfolio.pdf',
                      label: 'Faculty Portfolio',
                      icon: GraduationCap,
                      pages: 1,
                      status: selectedScenario === 'INST-03-LAND-CADRE-DISCREPANCY' ? 'flagged' : 'ok',
                      subtext: selectedScenario === 'INST-03-LAND-CADRE-DISCREPANCY' ? 'FSR 1:30 (Req 1:20)' : 'FSR & Cadre ratio met',
                    },
                  ].map((doc) => {
                    const Icon = doc.icon;
                    const isActive = activeDocument === doc.file;
                    return (
                      <div
                        key={doc.file}
                        onClick={() => {
                          setActiveDocument(doc.file);
                          setCurrentPage(1);
                        }}
                        className={`p-2.5 rounded-xl border text-xs cursor-pointer transition-all ${
                          isActive
                            ? 'bg-sky-50/70 border-sky-300 ring-1 ring-sky-300/40 shadow-xs'
                            : 'bg-white border-slate-200/80 hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-sky-600' : 'text-slate-400'}`} />
                            <span className="font-semibold text-slate-800">{doc.label}</span>
                          </div>
                          {doc.status === 'ok' ? (
                            <span className="h-4 w-4 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-[10px]">
                              ✓
                            </span>
                          ) : (
                            <span className="h-4 w-4 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-[10px] font-bold">
                              !
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] text-slate-500 mt-1 pl-5.5 truncate">
                          {doc.subtext}
                        </p>
                      </div>
                    );
                  })}

                  {/* Dynamically uploaded documents */}
                  {uploadedDocsList.map((docFile) => (
                    <div
                      key={docFile}
                      onClick={() => {
                        setActiveDocument(docFile);
                        setCurrentPage(1);
                      }}
                      className={`p-2.5 rounded-xl border text-xs cursor-pointer transition-all ${
                        activeDocument === docFile
                          ? 'bg-sky-50/70 border-sky-300 ring-1 ring-sky-300/40 shadow-xs'
                          : 'bg-white border-slate-200/80 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <FileText className={`w-3.5 h-3.5 ${activeDocument === docFile ? 'text-sky-600' : 'text-slate-400'}`} />
                          <span className="font-semibold text-slate-800 truncate w-32">{docFile}</span>
                        </div>
                        <span className="h-4 w-4 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-[10px]">
                          ✓
                        </span>
                      </div>
                      <p className="text-[10px] text-emerald-600 mt-1 pl-5.5 truncate font-medium">
                        User Ingested Evidence
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Document Authenticity Integrity Box */}
              <div className="mt-4 pt-3 border-t border-slate-200/80 text-[11px] space-y-2">
                <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                  Cryptographic Integrity
                </div>
                <div className="bg-slate-50 p-2 rounded-lg border border-slate-200 text-[10px] font-mono text-slate-600 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">SHA-256:</span>
                    <span className="text-emerald-700 font-bold">
                      {docMeta?.sha256_hash ? `${docMeta.sha256_hash.slice(0, 10)}...` : 'Verifying...'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Duplicate Check:</span>
                    <span className="text-sky-700 font-bold">No Collision (pHash)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* ═══════════════════════════════════════════════════════════════════════
                CENTER PANEL: DOCUMENT REVIEW VIEWER (Exact Layout from Reference Image 2)
            ════════════════════════════════════════════════════════════════════════ */}
            <div className="flex-1 flex flex-col bg-[#f0f3f7] border-r border-slate-200/90 overflow-hidden">
              {/* Document Header & Navigation Toolbar (Image 2 Center Header) */}
              <div className="bg-white border-b border-slate-200/80 px-5 py-2.5 flex items-center justify-between shadow-2xs shrink-0">
                {/* Left: Document Selector with < > navigation */}
                <div className="flex items-center gap-2">
                  <div className="flex items-center bg-slate-100 rounded-lg p-0.5 border border-slate-200 text-slate-600">
                    <button
                      onClick={() => {
                        const docs = ['Fire_Safety_NOC.pdf', 'Land_Title_Deed.pdf', 'Faculty_Portfolio.pdf'];
                        const idx = docs.indexOf(activeDocument);
                        if (idx > 0) setActiveDocument(docs[idx - 1]);
                      }}
                      className="p-1 hover:bg-white rounded transition"
                      title="Previous Document"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => {
                        const docs = ['Fire_Safety_NOC.pdf', 'Land_Title_Deed.pdf', 'Faculty_Portfolio.pdf'];
                        const idx = docs.indexOf(activeDocument);
                        if (idx < docs.length - 1) setActiveDocument(docs[idx + 1]);
                      }}
                      className="p-1 hover:bg-white rounded transition"
                      title="Next Document"
                    >
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="flex items-center gap-1.5 ml-1">
                    <FileText className="w-4 h-4 text-sky-600" />
                    <span className="text-xs font-bold text-slate-800">
                      {activeDocument.replace(/_/g, ' ').replace('.pdf', '')}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
                      PDF
                    </span>
                  </div>

                  {/* Warning Pill if flagged */}
                  {selectedScenario !== 'INST-01-COMPLIANT' && (
                    <span className="ml-2 flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-bold">
                      <AlertTriangle className="w-3 h-3 text-amber-500" />
                      Advisory Scrutiny Flagged
                    </span>
                  )}
                </div>

                {/* Right: Zoom & Pagination controls (Exact Image 2 toolbar) */}
                <div className="flex items-center gap-3">
                  {/* Zoom Controls */}
                  <div className="flex items-center gap-1 bg-slate-100 px-2 py-1 rounded-lg border border-slate-200 text-xs">
                    <button
                      onClick={() => setZoomLevel((z) => Math.max(0.7, z - 0.1))}
                      className="p-0.5 text-slate-600 hover:text-slate-900"
                      title="Zoom Out"
                    >
                      <ZoomOut className="w-3.5 h-3.5" />
                    </button>
                    <span className="text-[11px] font-mono text-slate-700 w-9 text-center font-semibold">
                      {Math.round(zoomLevel * 100)}%
                    </span>
                    <button
                      onClick={() => setZoomLevel((z) => Math.min(1.5, z + 0.1))}
                      className="p-0.5 text-slate-600 hover:text-slate-900"
                      title="Zoom In"
                    >
                      <ZoomIn className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Pagination Pill */}
                  <div className="flex items-center bg-slate-100 px-1 py-0.5 rounded-lg border border-slate-200 text-xs">
                    <button
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      className="px-1.5 py-0.5 text-slate-500 hover:text-slate-800 font-bold"
                    >
                      ‹
                    </button>
                    <span className="px-2 py-0.5 bg-white rounded text-[11px] font-bold text-sky-600 shadow-2xs border border-slate-200">
                      {currentPage}
                    </span>
                    <button
                      onClick={() => setCurrentPage((p) => p + 1)}
                      className="px-1.5 py-0.5 text-slate-500 hover:text-slate-800 font-bold"
                    >
                      ›
                    </button>
                  </div>

                  {/* ELA Heatmap Toggle */}
                  <button
                    onClick={() => setShowHeatmap(!showHeatmap)}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition border ${
                      showHeatmap
                        ? 'bg-amber-500 text-white border-amber-600 shadow-xs'
                        : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                    }`}
                    title="Toggle pixel-by-pixel Error Level Analysis (ELA) compression heatmap"
                  >
                    <Layers className="w-3.5 h-3.5 text-amber-500" />
                    <span>{showHeatmap ? 'ELA Heatmap [ON]' : 'ELA Heatmap'}</span>
                  </button>
                </div>
              </div>

              {/* Document Canvas Display */}
              <div className="flex-1 relative overflow-auto p-6 flex justify-center items-start">
                <div
                  style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'top center' }}
                  className="relative transition-transform duration-200 shadow-xl rounded-xl overflow-hidden border border-slate-300 bg-white"
                >
                  {/* Document Page Image (Rendered with PyMuPDF with zero iframe scaling drift) */}
                  <img
                    src={`/api/v1/documents/${selectedScenario}/${activeDocument}/render?page=${currentPage}&dpi=150`}
                    alt="Document Evidence"
                    className="w-[580px] block"
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
                      className="border-2 border-sky-600 bg-sky-500/20 rounded pointer-events-none pulse-highlight shadow-md z-20 flex items-start"
                    >
                      <span className="absolute -top-5 left-0 bg-sky-600 text-white font-bold text-[9px] px-2 py-0.5 rounded shadow-xs tracking-wider">
                        EXTRACTED EVIDENCE
                      </span>
                    </div>
                  )}

                  {/* Real ELA Compression Heatmap Overlay */}
                  {showHeatmap && (
                    <img
                      src={`/api/v1/documents/${selectedScenario}/${activeDocument}/ela?page=${currentPage}`}
                      alt="ELA Heatmap"
                      className="absolute inset-0 w-[580px] h-full object-cover mix-blend-multiply opacity-80 pointer-events-none z-30"
                    />
                  )}
                </div>
              </div>
            </div>

            {/* ═══════════════════════════════════════════════════════════════════════
                RIGHT PANEL: AI-EXTRACTED OBSERVATIONS (Exact Image 2 Observation Cards)
            ════════════════════════════════════════════════════════════════════════ */}
            <div className="w-96 bg-white flex flex-col shrink-0 shadow-sm overflow-hidden">
              {/* Header: AI-Extracted Observations with Lightbulb */}
              <div className="p-4 border-b border-slate-200/80 bg-white">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-7 w-7 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center">
                      <Lightbulb className="w-4 h-4 text-amber-500" />
                    </div>
                    <div>
                      <h3 className="text-xs font-bold text-slate-800">
                        AI-Extracted Observations
                      </h3>
                      <p className="text-[10px] text-slate-500">
                        Multi-signal validation across 3 statutory pillars
                      </p>
                    </div>
                  </div>

                  <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 font-bold">
                    {filteredFindings.length} Items
                  </span>
                </div>

                {/* 3 Pillars Filter Buttons */}
                <div className="grid grid-cols-4 gap-1 mt-3">
                  {[
                    { id: 'ALL', label: 'All', count: allFindings.length },
                    { id: 'AUTHENTICITY', label: 'Authentic', count: authenticityFindings.length },
                    { id: 'COMPLETENESS', label: 'Complete', count: completenessFindings.length },
                    { id: 'REGULATORY_COMPLIANCE', label: 'Statutory', count: complianceFindings.length },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActivePillarTab(tab.id as any)}
                      className={`py-1 px-1 rounded-lg text-[10px] font-semibold transition text-center truncate ${
                        activePillarTab === tab.id
                          ? 'bg-sky-50 text-sky-700 border border-sky-300 font-bold shadow-2xs'
                          : 'bg-slate-50 text-slate-500 hover:text-slate-700 border border-slate-200/70'
                      }`}
                    >
                      {tab.label} ({tab.count})
                    </button>
                  ))}
                </div>
              </div>

              {/* Observation Cards List */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-[#f8fafc]">
                {loading ? (
                  <div className="flex flex-col items-center justify-center h-48 text-slate-400 text-xs">
                    <RefreshCw className="w-5 h-5 animate-spin mb-2 text-sky-600" />
                    <span>Cross-verifying evidence against APH 2024–27...</span>
                  </div>
                ) : filteredFindings.length === 0 ? (
                  <div className="text-center py-12 text-slate-400 text-xs">
                    No observations found under this pillar.
                  </div>
                ) : (
                  filteredFindings.map((finding) => {
                    const isSelected = selectedFinding?.finding_id === finding.finding_id;
                    const isCompliant = finding.outcome === 'Compliant';
                    const isDiscrepancy = finding.outcome === 'Discrepancy Found';

                    return (
                      <div
                        key={finding.finding_id}
                        onClick={() => handleInspectFinding(finding)}
                        className={`rounded-xl border p-3.5 transition cursor-pointer relative bg-white ${
                          isSelected
                            ? 'border-sky-500 ring-2 ring-sky-500/20 shadow-md'
                            : 'border-slate-200/80 hover:border-slate-300 hover:shadow-xs'
                        }`}
                      >
                        {/* Top row: Title + Status Pill (Image 2 style) */}
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <span className="text-[10px] font-mono text-sky-700 font-semibold">
                              {finding.applicable_rule?.clause_reference || 'Statutory Norm'}
                            </span>
                            <h4 className="text-xs font-bold text-slate-800">
                              {finding.title}
                            </h4>
                          </div>

                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 flex items-center gap-1 ${
                              isCompliant
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : isDiscrepancy
                                ? 'bg-red-50 text-red-700 border border-red-200'
                                : 'bg-amber-50 text-amber-700 border border-amber-200'
                            }`}
                          >
                            {isCompliant ? (
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            ) : isDiscrepancy ? (
                              <AlertTriangle className="w-3 h-3 text-red-600" />
                            ) : (
                              <HelpCircle className="w-3 h-3 text-amber-600" />
                            )}
                            {finding.outcome === 'Compliant'
                              ? 'Compliant'
                              : finding.outcome === 'Discrepancy Found'
                              ? 'Conflicting'
                              : 'Review Needed'}
                          </span>
                        </div>

                        {/* Description */}
                        <p className="text-[11px] text-slate-600 mt-1.5 leading-relaxed">
                          {finding.description}
                        </p>

                        {/* Value Comparison Tiles (Exact Image 2 Observation Box) */}
                        <div className="mt-3 pt-2 border-t border-slate-100">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-slate-50 p-2 rounded-lg border border-slate-200 text-center">
                              <span className="text-[9px] uppercase tracking-wider text-slate-400 block font-semibold">
                                Extracted Evidence
                              </span>
                              <span className="text-xs font-bold text-slate-800 font-mono">
                                {finding.evidence.extracted_value}
                              </span>
                            </div>

                            <ArrowRight className="w-3 h-3 text-slate-400 shrink-0" />

                            <div className="flex-1 bg-slate-50 p-2 rounded-lg border border-slate-200 text-center">
                              <span className="text-[9px] uppercase tracking-wider text-slate-400 block font-semibold">
                                Statutory Requirement
                              </span>
                              <span className="text-xs font-bold text-sky-800 font-mono">
                                {finding.applicable_rule?.statutory_basis || 'Standard Norm'}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Card Footer: Inspect Evidence button & Document citation */}
                        <div className="mt-3 flex items-center justify-between text-[11px]">
                          <span className="text-slate-400 font-mono text-[10px]">
                            {finding.evidence.source_document_name}
                          </span>

                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleInspectFinding(finding);
                            }}
                            className="text-sky-600 hover:text-sky-800 font-semibold text-xs flex items-center gap-1 group"
                          >
                            <span>Inspect Evidence</span>
                            <ChevronRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Bottom Action Footer: Officer Resolution Buttons & Upload Corrected Document (Exact Image 2) */}
              <div className="p-3.5 border-t border-slate-200 bg-white space-y-2.5">
                {selectedFinding ? (
                  <div className="space-y-1.5">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      Officer Decision Support
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={() => recordOfficerDecision('ACCEPTED')}
                        className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 shadow-sm transition"
                      >
                        <Check className="w-3.5 h-3.5" />
                        Accept Finding
                      </button>
                      <button
                        onClick={() => recordOfficerDecision('REFERRED_FOR_INSPECTION', 'Physical inspection recommended')}
                        className="w-full py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 shadow-sm transition"
                      >
                        <AlertTriangle className="w-3.5 h-3.5" />
                        Mark Inspection
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="text-[11px] text-slate-400 text-center py-0.5">
                    Select an observation above to inspect and take action.
                  </div>
                )}

                {/* Upload Corrected Document Button from Reference Image 2 */}
                <button
                  onClick={() => {
                    setUploadResult(null);
                    setUploadError(null);
                    setUploadFile(null);
                    setShowUploadModal(true);
                  }}
                  className="w-full py-2.5 px-4 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 font-semibold text-xs rounded-xl flex items-center justify-center gap-2 shadow-2xs transition hover:border-slate-400"
                >
                  <span>Upload Corrected Document</span>
                  <UploadCloud className="w-4 h-4 text-slate-500" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ─────────────────────────────────────────────────────────────────────────
            VIEW 2: AUDIT TRAIL TIMELINE & FILTER CONTROLS (Exact Reference Image 1)
        ────────────────────────────────────────────────────────────────────────── */}
        {currentView === 'AUDIT_TIMELINE' && (
          <div className="flex-1 flex overflow-hidden">
            {/* Filter Controls Sidebar (Left Column from Reference Image 1) */}
            <div className="w-72 bg-white border-r border-slate-200 p-5 flex flex-col justify-between shrink-0 overflow-y-auto">
              <div className="space-y-5">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                    <Filter className="w-4 h-4 text-sky-600" />
                    Filter Controls
                  </h3>
                  <button
                    onClick={() => setTimelineFilterStatus('ALL')}
                    className="text-xs text-slate-400 hover:text-slate-600"
                  >
                    Reset
                  </button>
                </div>

                {/* Date Range Section */}
                <div>
                  <div className="flex items-center justify-between text-xs font-bold text-slate-700 mb-2">
                    <span>Date Range</span>
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                  </div>
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-600">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>Start Date: 2024-01-01</span>
                    </div>
                    <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-600">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>End Date: 2024-10-31</span>
                    </div>
                  </div>
                </div>

                {/* User / Scrutiny Officer Dropdown */}
                <div>
                  <div className="flex items-center justify-between text-xs font-bold text-slate-700 mb-2">
                    <span>Scrutiny Officer</span>
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                  </div>
                  <select className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 font-medium focus:outline-none">
                    <option>AICTE-OFFICER-409 (Active)</option>
                    <option>John D. (Regional Officer)</option>
                    <option>Sarah K. (Legal Advisor)</option>
                    <option>Michael R. (Technical Expert)</option>
                    <option>All Officers</option>
                  </select>
                </div>

                {/* Revision / Resolution Status Pills */}
                <div>
                  <div className="flex items-center justify-between text-xs font-bold text-slate-700 mb-2">
                    <span>Scrutiny Status</span>
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                  </div>
                  <div className="space-y-1.5 text-xs">
                    {[
                      { id: 'ALL', label: 'All Statuses', color: 'text-slate-600' },
                      { id: 'Approved', label: 'Approved', color: 'text-emerald-600' },
                      { id: 'In Review', label: 'In Review', color: 'text-amber-600' },
                      { id: 'Resolved', label: 'Resolved', color: 'text-sky-600' },
                    ].map((st) => (
                      <label
                        key={st.id}
                        onClick={() => setTimelineFilterStatus(st.id)}
                        className="flex items-center gap-2 cursor-pointer p-1 rounded hover:bg-slate-50"
                      >
                        <input
                          type="radio"
                          name="statusFilter"
                          checked={timelineFilterStatus === st.id}
                          onChange={() => setTimelineFilterStatus(st.id)}
                          className="text-sky-600 focus:ring-0"
                        />
                        <span className={`font-medium ${st.color}`}>{st.label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Compliance Standards Toggles */}
                <div>
                  <div className="flex items-center justify-between text-xs font-bold text-slate-700 mb-2">
                    <span>Compliance Standards</span>
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                  </div>
                  <div className="space-y-2 text-xs text-slate-600">
                    <div className="flex items-center justify-between">
                      <span>AICTE APH 2024–27</span>
                      <span className="w-7 h-4 bg-sky-500 rounded-full inline-block relative">
                        <span className="w-3 h-3 bg-white rounded-full absolute right-0.5 top-0.5" />
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>NBA Criteria 5 (FSR)</span>
                      <span className="w-7 h-4 bg-sky-500 rounded-full inline-block relative">
                        <span className="w-3 h-3 bg-white rounded-full absolute right-0.5 top-0.5" />
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>State Fire NOC Act</span>
                      <span className="w-7 h-4 bg-sky-500 rounded-full inline-block relative">
                        <span className="w-3 h-3 bg-white rounded-full absolute right-0.5 top-0.5" />
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-4 border-t border-slate-100 flex gap-2">
                <button
                  onClick={() => setTimelineFilterStatus('ALL')}
                  className="flex-1 py-1.5 px-3 border border-slate-200 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-50 transition"
                >
                  Clear Filters
                </button>
                <button
                  onClick={() => fetchAuditTrail()}
                  className="flex-1 py-1.5 px-3 bg-sky-600 text-white rounded-lg text-xs font-semibold hover:bg-sky-700 shadow-sm transition"
                >
                  Apply
                </button>
              </div>
            </div>

            {/* Audit Trail Timeline Cards View (Center/Right from Reference Image 1) */}
            <div className="flex-1 bg-[#f8fafc] p-6 overflow-y-auto">
              <div className="max-w-4xl mx-auto space-y-4">
                {/* Header row: Title + Date Filter + Search Bar */}
                <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                  <div>
                    <h2 className="text-base font-bold text-slate-800">
                      Audit Trail Timeline
                    </h2>
                    <p className="text-xs text-slate-500">
                      Cryptographically chained immutable scrutiny logs (SHA-256)
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg text-xs text-slate-700">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span className="font-semibold">Jan 2024 - Oct 2024</span>
                    </div>

                    <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg text-xs">
                      <Search className="w-3.5 h-3.5 text-slate-400" />
                      <input
                        type="text"
                        placeholder="Search audit events..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="bg-transparent focus:outline-none text-slate-800 placeholder-slate-400 w-40"
                      />
                    </div>
                  </div>
                </div>

                {/* Column Headers */}
                <div className="grid grid-cols-12 px-6 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <div className="col-span-3">Timestamp</div>
                  <div className="col-span-2">Revision / Stage</div>
                  <div className="col-span-3">Officer / Actor</div>
                  <div className="col-span-2">Status</div>
                  <div className="col-span-2 text-right">Associated</div>
                </div>

                {/* Timeline Cards Container with Connecting Vertical Rail */}
                <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-4 before:bottom-4 before:w-0.5 before:bg-slate-200">
                  {auditEvents.length === 0 ? (
                    <div className="bg-white p-8 rounded-xl border border-slate-200 text-center text-slate-400 text-xs">
                      No audit events recorded yet. Perform an officer action in Document Review to append.
                    </div>
                  ) : (
                    auditEvents
                      .filter((e) => {
                        if (!searchQuery) return true;
                        return (
                          e.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          e.actor_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          e.event_id.toLowerCase().includes(searchQuery.toLowerCase())
                        );
                      })
                      .map((event, index) => {
                        const isApproved = event.action.includes('ACCEPTED') || event.action.includes('COMPLIANT');
                        const isReview = event.action.includes('INSPECTION') || event.action.includes('PENDING');

                        return (
                          <div
                            key={event.event_id}
                            className={`relative bg-white rounded-xl border p-4 shadow-2xs transition hover:shadow-xs ${
                              isApproved
                                ? 'border-l-4 border-l-emerald-500 border-slate-200'
                                : isReview
                                ? 'border-l-4 border-l-amber-500 border-slate-200'
                                : 'border-l-4 border-l-sky-500 border-slate-200'
                            }`}
                          >
                            {/* Circular Timeline Node on the Left Rail */}
                            <span
                              className={`absolute -left-[27px] top-6 w-3.5 h-3.5 rounded-full border-2 border-white shadow-xs ${
                                isApproved
                                  ? 'bg-emerald-500'
                                  : isReview
                                  ? 'bg-amber-500'
                                  : 'bg-sky-500'
                              }`}
                            />

                            {/* Top Row: Date, Rev, User, Status Pill, Badges */}
                            <div className="grid grid-cols-12 items-center text-xs">
                              <div className="col-span-3 font-semibold text-slate-800">
                                {event.timestamp ? event.timestamp.replace('T', ' ').slice(0, 16) : '2024-05-18 10:30'}
                              </div>

                              <div className="col-span-2 font-mono text-slate-500 font-medium">
                                #{event.sequence_number || index + 1} · Rev {index + 1} → {index + 2}
                              </div>

                              <div className="col-span-3 font-semibold text-slate-700 flex items-center gap-1.5">
                                <span className="h-5 w-5 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center text-[10px] font-bold text-slate-600">
                                  {event.actor_id ? event.actor_id.slice(0, 1) : 'A'}
                                </span>
                                <span>{event.actor_id || 'AICTE-OFFICER-409'}</span>
                              </div>

                              <div className="col-span-2">
                                <span
                                  className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold inline-flex items-center gap-1 ${
                                    isApproved
                                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                      : isReview
                                      ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                      : 'bg-sky-50 text-sky-700 border border-sky-200'
                                  }`}
                                >
                                  {isApproved ? (
                                    <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                                  ) : isReview ? (
                                    <Clock className="w-3 h-3 text-amber-600" />
                                  ) : (
                                    <Check className="w-3 h-3 text-sky-600" />
                                  )}
                                  {isApproved ? 'Approved' : isReview ? 'In Review' : 'Resolved'}
                                </span>
                              </div>

                              {/* Badges on Right (AICTE, NBA, ISO) matching Image 1 */}
                              <div className="col-span-2 flex items-center justify-end gap-1.5">
                                <span className="h-6 w-6 rounded-full bg-sky-50 border border-sky-200 text-sky-700 flex items-center justify-center text-[9px] font-extrabold" title="AICTE APH 2024-27">
                                  AICTE
                                </span>
                                <span className="h-6 w-6 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 flex items-center justify-center text-[9px] font-extrabold" title="NBA Standard">
                                  NBA
                                </span>
                                <span className="h-6 w-6 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 flex items-center justify-center text-[8px] font-bold" title="ISO 9001 Certified">
                                  ISO
                                </span>
                              </div>
                            </div>

                            {/* Middle Row: Description */}
                            <div className="mt-2.5 text-xs text-slate-600 leading-relaxed">
                              Action recorded: <strong className="text-slate-800">{event.action}</strong>
                              <span className="text-slate-400 ml-2 font-mono text-[10px]">
                                Event ID: {event.event_id}
                              </span>
                            </div>

                            {/* Bottom Row: View Diff & Progress Bar matching Image 1 */}
                            <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs">
                              <button
                                onClick={() => setCurrentView('DOCUMENT_REVIEW')}
                                className="text-sky-600 hover:text-sky-800 font-semibold text-xs flex items-center gap-1"
                              >
                                <span>Inspect Evidence & Diff</span>
                                <ChevronRight className="w-3 h-3" />
                              </button>

                              {/* Progress Bar & Percentage (Image 1 feature) */}
                              <div className="flex items-center gap-3">
                                <div className="w-32 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                                  <div
                                    className={`h-full rounded-full ${
                                      isApproved ? 'bg-emerald-500' : isReview ? 'bg-amber-500' : 'bg-sky-500'
                                    }`}
                                    style={{ width: isApproved ? '100%' : isReview ? '60%' : '100%' }}
                                  />
                                </div>
                                <span className="text-[11px] font-bold text-slate-700 w-8 text-right">
                                  {isApproved ? '100%' : isReview ? '60%' : '100%'}
                                </span>
                              </div>
                            </div>
                          </div>
                        );
                      })
                  )}
                </div>

                {/* Footer Pagination matching Image 1 */}
                <div className="flex items-center justify-between pt-4 text-xs text-slate-500">
                  <span>Showing 1-{auditEvents.length} of {auditEvents.length} events · Page 1 of 1</span>
                  <button
                    onClick={() => {
                      const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(auditEvents, null, 2));
                      const downloadAnchor = document.createElement('a');
                      downloadAnchor.setAttribute('href', dataStr);
                      downloadAnchor.setAttribute('download', `audit_trail_${selectedScenario}.json`);
                      document.body.appendChild(downloadAnchor);
                      downloadAnchor.click();
                      downloadAnchor.remove();
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-700 font-semibold hover:bg-slate-50 transition shadow-2xs"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Export Audit Trail</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ─────────────────────────────────────────────────────────────────────────
            VIEW 3: APH 2024–2027 HANDBOOK RULES & STATUTORY NORMS
        ────────────────────────────────────────────────────────────────────────── */}
        {currentView === 'APH_RULES' && (
          <div className="flex-1 bg-[#f8fafc] p-6 overflow-y-auto">
            <div className="max-w-5xl mx-auto space-y-4">
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-xl bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600">
                    <BookOpen className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-slate-800">
                      AICTE Approval Process Handbook (APH 2024–2027) Regulatory Engine
                    </h2>
                    <p className="text-xs text-slate-500">
                      Official statutory clauses implemented in the automated scrutiny evaluator
                    </p>
                  </div>
                </div>
              </div>

              {/* Rules Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {aphRules.map((rule) => (
                  <div key={rule.rule_id} className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-50 text-sky-700 border border-sky-200 font-bold">
                        {rule.clause_reference}
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        Rule ID: {rule.rule_id}
                      </span>
                    </div>

                    <h3 className="text-xs font-bold text-slate-800 mt-2">
                      {rule.title}
                    </h3>
                    <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                      {rule.description}
                    </p>

                    <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px]">
                      <span className="text-slate-500">
                        Pillar: <strong>{rule.assessment_pillar}</strong>
                      </span>
                      <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded text-[10px] font-semibold border border-emerald-200">
                        Active Statutory Rule
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ─────────────────────────────────────────────────────────────────────────
          DOCUMENT UPLOAD MODAL & STATUTORY INGESTION SECTION
      ────────────────────────────────────────────────────────────────────────── */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white border border-slate-200 w-full max-w-xl rounded-2xl shadow-2xl overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600">
                  <UploadCloud className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-800">
                    Statutory Evidence Document Ingestion
                  </h3>
                  <p className="text-xs text-slate-500">
                    Hash-verified ingestion with automated SHA-256 integrity checks
                  </p>
                </div>
              </div>

              <button
                onClick={() => setShowUploadModal(false)}
                className="h-8 w-8 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 flex items-center justify-center transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleFileUpload} className="p-6 space-y-4 text-xs">
              {/* Application Context */}
              <div className="space-y-1.5">
                <label className="font-bold text-slate-700">Target Application / Scrutiny Case</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setUploadScenarioTarget('CURRENT')}
                    className={`p-2.5 rounded-xl border text-left transition ${
                      uploadScenarioTarget === 'CURRENT'
                        ? 'border-sky-500 bg-sky-50/60 ring-1 ring-sky-300'
                        : 'border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    <span className="font-bold text-slate-800 block truncate">Current Application</span>
                    <span className="text-[10px] text-slate-500 block truncate">{selectedScenario}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setUploadScenarioTarget('NEW')}
                    className={`p-2.5 rounded-xl border text-left transition ${
                      uploadScenarioTarget === 'NEW'
                        ? 'border-sky-500 bg-sky-50/60 ring-1 ring-sky-300'
                        : 'border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    <span className="font-bold text-slate-800 block">Register New Case</span>
                    <span className="text-[10px] text-slate-500 block">Custom Institution Input</span>
                  </button>
                </div>

                {uploadScenarioTarget === 'NEW' && (
                  <div className="pt-2 grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-slate-500 block font-semibold">Institution Name</label>
                      <input
                        type="text"
                        placeholder="e.g. National Institute of Tech"
                        value={customInstitutionName}
                        onChange={(e) => setCustomInstitutionName(e.target.value)}
                        className="w-full mt-1 p-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-xs focus:outline-none focus:border-sky-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-500 block font-semibold">Case Identifier Code</label>
                      <input
                        type="text"
                        placeholder="e.g. INST-05-NEW"
                        value={customScenarioId}
                        onChange={(e) => setCustomScenarioId(e.target.value)}
                        className="w-full mt-1 p-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-xs uppercase font-mono focus:outline-none focus:border-sky-500"
                        required
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Document Classification */}
              <div className="space-y-1.5">
                <label className="font-bold text-slate-700">Document Classification / Statutory Type</label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'Fire_Safety_NOC', label: 'Fire Safety Certificate', icon: Flame, note: 'State Fire Service NOC' },
                    { id: 'Land_Title_Deed', label: 'Land Title Deed', icon: Building2, note: 'FAR & Ownership verification' },
                    { id: 'Faculty_Portfolio', label: 'Faculty Portfolio', icon: GraduationCap, note: 'FSR & Cadre ratio audit' },
                    { id: 'Other_Evidence', label: 'Other Statutory Evidence', icon: FileText, note: 'Supplemental compliance PDF' },
                  ].map((dt) => {
                    const Icon = dt.icon;
                    return (
                      <div
                        key={dt.id}
                        onClick={() => setUploadDocType(dt.id)}
                        className={`p-2.5 rounded-xl border cursor-pointer transition ${
                          uploadDocType === dt.id
                            ? 'border-sky-500 bg-sky-50/50 ring-1 ring-sky-300'
                            : 'border-slate-200 hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-center gap-1.5 font-bold text-slate-800">
                          <Icon className={`w-3.5 h-3.5 ${uploadDocType === dt.id ? 'text-sky-600' : 'text-slate-400'}`} />
                          <span className="truncate">{dt.label}</span>
                        </div>
                        <span className="text-[10px] text-slate-500 block mt-0.5 truncate">{dt.note}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Drag & Drop File Upload Area */}
              <div className="space-y-1.5">
                <label className="font-bold text-slate-700">Select File</label>
                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragActive(true);
                  }}
                  onDragLeave={() => setDragActive(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragActive(false);
                    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                      setUploadFile(e.dataTransfer.files[0]);
                    }
                  }}
                  className={`border-2 border-dashed rounded-xl p-5 text-center transition cursor-pointer ${
                    dragActive
                      ? 'border-sky-500 bg-sky-50/50'
                      : uploadFile
                      ? 'border-emerald-400 bg-emerald-50/30'
                      : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
                  }`}
                  onClick={() => document.getElementById('hidden-file-input')?.click()}
                >
                  <input
                    id="hidden-file-input"
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setUploadFile(e.target.files[0]);
                      }
                    }}
                  />

                  {uploadFile ? (
                    <div className="flex items-center justify-between bg-white p-3 rounded-lg border border-slate-200 shadow-2xs">
                      <div className="flex items-center gap-2.5 text-left">
                        <div className="h-8 w-8 rounded-lg bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="font-bold text-slate-800 text-xs truncate max-w-xs">{uploadFile.name}</div>
                          <div className="text-[10px] text-slate-400">
                            {(uploadFile.size / 1024).toFixed(1)} KB · {uploadFile.type || 'Document'}
                          </div>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setUploadFile(null);
                        }}
                        className="text-xs text-red-500 hover:text-red-700 font-semibold px-2 py-1 rounded hover:bg-red-50"
                      >
                        Remove
                      </button>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-1.5 py-2">
                      <div className="h-9 w-9 rounded-full bg-sky-50 flex items-center justify-center text-sky-500">
                        <FileUp className="w-4 h-4" />
                      </div>
                      <div className="font-semibold text-slate-700 text-xs">
                        Click to browse or drag and drop your document
                      </div>
                      <div className="text-[10px] text-slate-400">
                        Supports PDF, JPEG, PNG up to 25MB (Auto SHA-256 hashed)
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Status & Error Feedback */}
              {uploadError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}

              {uploadResult && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs space-y-1">
                  <div className="flex items-center gap-1.5 font-bold text-emerald-700">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>{uploadResult.message}</span>
                  </div>
                  <div className="font-mono text-[10px] text-emerald-600">
                    SHA-256: {uploadResult.sha256_hash.slice(0, 24)}...
                  </div>
                </div>
              )}

              {/* Form Action Buttons */}
              <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 border border-slate-200 rounded-xl text-slate-600 font-semibold hover:bg-slate-50 transition"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={uploading || !uploadFile}
                  className="px-5 py-2 bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white rounded-xl font-bold flex items-center gap-1.5 shadow-sm transition"
                >
                  {uploading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Ingesting & Hashing...</span>
                    </>
                  ) : (
                    <>
                      <UploadCloud className="w-4 h-4" />
                      <span>Upload & Run Scrutiny</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
