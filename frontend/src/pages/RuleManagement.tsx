import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuthStore } from '../store/authStore';
import { Shield, Plus, History, Settings, ChevronDown, ChevronRight, AlertTriangle, Trash2, RefreshCw } from 'lucide-react';

const API = 'http://localhost:8000/api/v1/rules';

interface CriticalRule {
  id: string;
  classification_code: string;
  attribute: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  conflict_behavior: string;
  version: number;
  is_latest: boolean;
  status: string;
  notes: string | null;
  created_by: string | null;
  created_at: string;
}

interface GlobalConfig {
  config_id: string;
  version: number;
  weight_semantic: number;
  weight_attribute: number;
  weight_manufacturer: number;
  weight_mpn: number;
  threshold_exact_duplicate: number;
  threshold_near_duplicate: number;
  threshold_functionally_equivalent: number;
  threshold_related: number;
  penalty_missing_attribute: number;
  penalty_critical_conflict: number;
  auto_approve_enabled: boolean;
  auto_approve_threshold: number;
  auto_approve_max_risk_level: string;
  high_risk_categories: string[];
  medium_risk_categories: string[];
  change_note: string | null;
  created_at: string;
}

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: 'bg-red-900/60 text-red-300 border-red-700',
  HIGH:     'bg-orange-900/60 text-orange-300 border-orange-700',
  MEDIUM:   'bg-yellow-900/60 text-yellow-300 border-yellow-700',
  LOW:      'bg-blue-900/60 text-blue-300 border-blue-700',
};

const RISK_COLORS: Record<string, string> = {
  LOW:      'text-green-400',
  MEDIUM:   'text-yellow-400',
  HIGH:     'text-orange-400',
  CRITICAL: 'text-red-400',
};

// ──────────────────────────────────────────────────────────────────────────────
// Sub-components
// ──────────────────────────────────────────────────────────────────────────────

function SectionHeader({ icon, title, subtitle }: { icon: React.ReactNode; title: string; subtitle: string }) {
  return (
    <div className="flex items-center gap-3 mb-6">
      <div className="p-2 bg-primary-900/50 rounded-lg border border-primary-800">{icon}</div>
      <div>
        <h2 className="text-xl font-bold text-gray-100">{title}</h2>
        <p className="text-sm text-gray-500">{subtitle}</p>
      </div>
    </div>
  );
}

function WeightBar({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-400">{label}</span>
        <span className="text-gray-200 font-mono">{(value * 100).toFixed(0)}%</span>
      </div>
      <input
        type="range" min={0} max={1} step={0.01} value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        className="w-full h-1.5 rounded-full accent-primary-500 bg-gray-800"
      />
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Main page
// ──────────────────────────────────────────────────────────────────────────────

export default function RuleManagement() {
  const { token, user } = useAuthStore();
  const isAdmin = (user as any)?.role === 'ADMIN';

  const headers = { Authorization: `Bearer ${token}` };

  // ── Critical Rules state ──
  const [rules, setRules] = useState<CriticalRule[]>([]);
  const [rulesLoading, setRulesLoading] = useState(false);
  const [ruleFilter, setRuleFilter] = useState('');
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  // Create rule form
  const [newCode, setNewCode]     = useState('');
  const [newAttr, setNewAttr]     = useState('');
  const [newSev, setNewSev]       = useState('CRITICAL');
  const [newBehavior, setNewBehavior] = useState('BLOCK_EQUIVALENCE');
  const [newNotes, setNewNotes]   = useState('');
  const [ruleError, setRuleError] = useState('');

  // ── Global Config state ──
  const [config, setConfig]         = useState<GlobalConfig | null>(null);
  const [configLoading, setConfigLoading] = useState(false);
  const [configDraft, setConfigDraft]     = useState<Partial<GlobalConfig>>({});
  const [configNote, setConfigNote]       = useState('');
  const [configError, setConfigError]     = useState('');
  const [configSuccess, setConfigSuccess] = useState('');

  // ── Active tab ──
  const [tab, setTab] = useState<'rules' | 'config' | 'audit'>('rules');
  const [auditLog, setAuditLog] = useState<any[]>([]);

  const loadRules = useCallback(async () => {
    setRulesLoading(true);
    try {
      const r = await axios.get(`${API}/critical-rules`, { headers });
      setRules(r.data);
    } catch { /* handled by global error boundary */ }
    finally { setRulesLoading(false); }
  }, [token]);

  const loadConfig = useCallback(async () => {
    setConfigLoading(true);
    try {
      const r = await axios.get(`${API}/config`, { headers });
      setConfig(r.data);
      setConfigDraft(r.data);
    } catch { /* no config yet */ }
    finally { setConfigLoading(false); }
  }, [token]);

  const loadAudit = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/audit?limit=50`, { headers });
      setAuditLog(r.data);
    } catch { /* */ }
  }, [token]);

  useEffect(() => { loadRules(); loadConfig(); loadAudit(); }, [loadRules, loadConfig, loadAudit]);

  // ── Group rules by category ──
  const grouped = rules
    .filter(r => r.classification_code.toLowerCase().includes(ruleFilter.toLowerCase()))
    .reduce<Record<string, CriticalRule[]>>((acc, r) => {
      (acc[r.classification_code] ||= []).push(r);
      return acc;
    }, {});

  // ── Create rule handler ──
  const handleCreateRule = async () => {
    setRuleError('');
    if (!newCode || !newAttr) { setRuleError('Category code and attribute are required.'); return; }
    try {
      await axios.post(`${API}/critical-rules`, {
        classification_code: newCode.toUpperCase(),
        attribute: newAttr.toLowerCase(),
        severity: newSev,
        conflict_behavior: newBehavior,
        notes: newNotes || null,
      }, { headers });
      setNewCode(''); setNewAttr(''); setNewNotes('');
      await loadRules();
      await loadAudit();
    } catch (e: any) {
      setRuleError(e.response?.data?.detail || 'Failed to create rule.');
    }
  };

  // ── Deactivate rule ──
  const handleDeactivate = async (ruleId: string) => {
    if (!window.confirm('Deactivate this rule? This action is logged.')) return;
    await axios.delete(`${API}/critical-rules/${ruleId}`, { headers });
    await loadRules();
    await loadAudit();
  };

  // ── Publish new global config ──
  const handlePublishConfig = async () => {
    setConfigError(''); setConfigSuccess('');
    const totalW = (configDraft.weight_semantic ?? 0) +
                   (configDraft.weight_attribute ?? 0) +
                   (configDraft.weight_manufacturer ?? 0) +
                   (configDraft.weight_mpn ?? 0);
    if (Math.abs(totalW - 1.0) > 0.01) {
      setConfigError(`Weights must sum to 1.0 (currently ${totalW.toFixed(2)})`);
      return;
    }
    try {
      await axios.post(`${API}/config`, { ...configDraft, change_note: configNote }, { headers });
      await loadConfig();
      await loadAudit();
      setConfigSuccess('New config published and version logged.');
    } catch (e: any) {
      setConfigError(e.response?.data?.detail || 'Failed to publish config.');
    }
  };

  // ──────────────────────────────────────────────────────────────────────────
  // Render
  // ──────────────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Shield className="text-primary-400 w-8 h-8" />
          <div>
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary-400 to-violet-400">
              Rule Management
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">Admin-governed critical rules, weights, and approval policy</p>
          </div>
        </div>
        {!isAdmin && (
          <div className="flex items-center gap-2 px-4 py-2 bg-yellow-900/30 border border-yellow-700 rounded-lg text-yellow-400 text-sm">
            <AlertTriangle className="w-4 h-4" />
            Read-only — Admin role required to modify rules
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-900 rounded-xl p-1 mb-6 w-fit border border-gray-800">
        {(['rules', 'config', 'audit'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-2 rounded-lg text-sm font-medium transition-all capitalize ${
              tab === t
                ? 'bg-primary-600 text-white shadow-lg shadow-primary-900/50'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {t === 'rules' ? 'Critical Rules' : t === 'config' ? 'Global Config' : 'Audit Trail'}
          </button>
        ))}
      </div>

      {/* ─────────────────────── CRITICAL RULES TAB ─────────────────────── */}
      {tab === 'rules' && (
        <div className="grid grid-cols-5 gap-6">
          {/* Left: tree view */}
          <div className="col-span-3 bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-xl">
            <SectionHeader
              icon={<Shield className="w-5 h-5 text-primary-400" />}
              title="Category Rules"
              subtitle={`${rules.length} active critical attribute rules`}
            />

            <input
              type="text"
              placeholder="Filter by category (e.g. VALVE)"
              value={ruleFilter}
              onChange={e => setRuleFilter(e.target.value)}
              className="w-full mb-4 bg-gray-950 border border-gray-800 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-600"
            />

            {rulesLoading ? (
              <div className="text-gray-600 animate-pulse text-sm">Loading rules…</div>
            ) : Object.keys(grouped).length === 0 ? (
              <div className="text-gray-600 text-sm">No rules found. Create one using the form →</div>
            ) : (
              <div className="space-y-2">
                {Object.entries(grouped).map(([code, attrs]) => (
                  <div key={code} className="rounded-lg border border-gray-800 overflow-hidden">
                    <button
                      className="w-full flex items-center justify-between px-4 py-3 bg-gray-800 hover:bg-gray-750 transition-colors"
                      onClick={() => setExpandedCategory(expandedCategory === code ? null : code)}
                    >
                      <span className="font-semibold text-gray-200">{code}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500">{attrs.length} rule{attrs.length !== 1 ? 's' : ''}</span>
                        {expandedCategory === code ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
                      </div>
                    </button>
                    {expandedCategory === code && (
                      <div className="divide-y divide-gray-800">
                        {attrs.map(rule => (
                          <div key={rule.id} className="px-4 py-3 flex items-center justify-between bg-gray-900/50">
                            <div className="flex items-center gap-3">
                              <code className="text-primary-300 text-sm bg-primary-950/50 px-2 py-0.5 rounded">
                                {rule.attribute}
                              </code>
                              <span className={`text-xs px-2 py-0.5 rounded-full border ${SEVERITY_COLORS[rule.severity]}`}>
                                {rule.severity}
                              </span>
                              <span className="text-xs text-gray-500">{rule.conflict_behavior}</span>
                            </div>
                            <div className="flex items-center gap-2 text-xs text-gray-600">
                              <span>v{rule.version}</span>
                              {isAdmin && (
                                <button
                                  onClick={() => handleDeactivate(rule.id)}
                                  className="p-1 hover:text-red-400 text-gray-600 transition-colors"
                                  title="Deactivate"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right: create form */}
          <div className="col-span-2 space-y-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-xl">
              <SectionHeader
                icon={<Plus className="w-5 h-5 text-green-400" />}
                title="Add Critical Rule"
                subtitle="Admin only"
              />
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Category Code</label>
                  <input
                    placeholder="VALVE, MOTOR, PIPE…"
                    value={newCode}
                    onChange={e => setNewCode(e.target.value)}
                    disabled={!isAdmin}
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-600 disabled:opacity-40"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Attribute</label>
                  <input
                    placeholder="pressure_class, voltage…"
                    value={newAttr}
                    onChange={e => setNewAttr(e.target.value)}
                    disabled={!isAdmin}
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-600 disabled:opacity-40"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">Severity</label>
                    <select value={newSev} onChange={e => setNewSev(e.target.value)} disabled={!isAdmin}
                      className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm disabled:opacity-40">
                      {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(s => <option key={s}>{s}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">Conflict Behavior</label>
                    <select value={newBehavior} onChange={e => setNewBehavior(e.target.value)} disabled={!isAdmin}
                      className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm disabled:opacity-40">
                      {['BLOCK_EQUIVALENCE', 'REQUIRE_REVIEW', 'FLAG_ONLY'].map(b => <option key={b}>{b}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Notes (optional)</label>
                  <textarea
                    rows={2}
                    placeholder="Rationale for this rule…"
                    value={newNotes}
                    onChange={e => setNewNotes(e.target.value)}
                    disabled={!isAdmin}
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm resize-none disabled:opacity-40"
                  />
                </div>
                {ruleError && <p className="text-red-400 text-xs">{ruleError}</p>}
                <button
                  onClick={handleCreateRule}
                  disabled={!isAdmin}
                  className="w-full py-2 rounded-lg font-medium text-sm transition-all bg-gradient-to-r from-primary-700 to-primary-600 hover:from-primary-600 hover:to-primary-500 text-white shadow-lg disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Create Rule
                </button>
              </div>
            </div>

            {/* Category risk quick reference */}
            {config && (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-xs space-y-3">
                <p className="text-gray-400 font-medium">Risk Category Registry</p>
                <div>
                  <span className="text-red-400 font-medium">HIGH RISK: </span>
                  <span className="text-gray-400">{config.high_risk_categories.join(', ')}</span>
                </div>
                <div>
                  <span className="text-yellow-400 font-medium">MEDIUM RISK: </span>
                  <span className="text-gray-400">{config.medium_risk_categories.join(', ')}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────── GLOBAL CONFIG TAB ─────────────────────── */}
      {tab === 'config' && (
        <div className="grid grid-cols-2 gap-6">
          {configLoading ? (
            <div className="col-span-2 text-gray-600 animate-pulse text-sm">Loading config…</div>
          ) : (
            <>
              {/* Weights & Thresholds */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-xl">
                <SectionHeader
                  icon={<Settings className="w-5 h-5 text-violet-400" />}
                  title="Matching Weights"
                  subtitle="Must sum to 100%"
                />
                {config && (
                  <div className="space-y-5">
                    {(
                      [
                        ['Semantic Similarity', 'weight_semantic'],
                        ['Attribute Match', 'weight_attribute'],
                        ['Manufacturer Match', 'weight_manufacturer'],
                        ['MPN Match', 'weight_mpn'],
                      ] as [string, keyof GlobalConfig][]
                    ).map(([label, key]) => (
                      <WeightBar
                        key={key}
                        label={label}
                        value={(configDraft[key] as number) ?? 0}
                        onChange={v => setConfigDraft(d => ({ ...d, [key]: parseFloat(v.toFixed(2)) }))}
                      />
                    ))}
                    <div className={`text-xs font-mono text-right mt-1 ${
                      Math.abs(((configDraft.weight_semantic ?? 0) + (configDraft.weight_attribute ?? 0) +
                        (configDraft.weight_manufacturer ?? 0) + (configDraft.weight_mpn ?? 0)) - 1.0) > 0.01
                        ? 'text-red-400' : 'text-green-400'
                    }`}>
                      Total: {(
                        ((configDraft.weight_semantic ?? 0) + (configDraft.weight_attribute ?? 0) +
                        (configDraft.weight_manufacturer ?? 0) + (configDraft.weight_mpn ?? 0)) * 100
                      ).toFixed(0)}%
                    </div>
                  </div>
                )}

                <hr className="border-gray-800 my-5" />
                <p className="text-sm font-medium text-gray-400 mb-4">Match-Type Thresholds</p>
                <div className="space-y-2 text-sm">
                  {([
                    ['Exact Duplicate', 'threshold_exact_duplicate'],
                    ['Near Duplicate', 'threshold_near_duplicate'],
                    ['Functionally Equivalent', 'threshold_functionally_equivalent'],
                    ['Related', 'threshold_related'],
                  ] as [string, keyof GlobalConfig][]).map(([label, key]) => (
                    <div key={key} className="flex items-center justify-between">
                      <span className="text-gray-500">{label}</span>
                      <input
                        type="number" min={0} max={1} step={0.01}
                        value={(configDraft[key] as number) ?? 0}
                        onChange={e => setConfigDraft(d => ({ ...d, [key]: parseFloat(e.target.value) }))}
                        disabled={!isAdmin}
                        className="w-20 text-right bg-gray-950 border border-gray-800 rounded px-2 py-0.5 font-mono text-xs disabled:opacity-40"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Approval Policy */}
              <div className="space-y-5">
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-xl">
                  <SectionHeader
                    icon={<AlertTriangle className="w-5 h-5 text-yellow-400" />}
                    title="Automatic Approval Policy"
                    subtitle="Controls system-autonomous approvals"
                  />
                  <div className="space-y-4">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={configDraft.auto_approve_enabled ?? false}
                        onChange={e => setConfigDraft(d => ({ ...d, auto_approve_enabled: e.target.checked }))}
                        disabled={!isAdmin}
                        className="w-4 h-4 accent-primary-500 disabled:opacity-40"
                      />
                      <span className="text-sm text-gray-300">Enable automatic approvals</span>
                    </label>
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">Auto-approve Threshold</label>
                      <input type="number" min={0} max={1} step={0.01}
                        value={configDraft.auto_approve_threshold ?? 0.95}
                        onChange={e => setConfigDraft(d => ({ ...d, auto_approve_threshold: parseFloat(e.target.value) }))}
                        disabled={!isAdmin}
                        className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm font-mono disabled:opacity-40"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">Max Risk Level for Auto-Approve</label>
                      <select
                        value={configDraft.auto_approve_max_risk_level ?? 'LOW'}
                        onChange={e => setConfigDraft(d => ({ ...d, auto_approve_max_risk_level: e.target.value }))}
                        disabled={!isAdmin}
                        className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm disabled:opacity-40"
                      >
                        {['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map(r => (
                          <option key={r} className={RISK_COLORS[r]}>{r}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                {/* Active config snapshot */}
                {config && (
                  <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-xs text-gray-500 space-y-1">
                    <p className="text-gray-400 font-medium mb-2">Currently Active: v{config.version}</p>
                    <p>Config ID: <code className="text-gray-300">{config.config_id.split('-')[0]}…</code></p>
                    <p>Published: {new Date(config.created_at).toLocaleDateString()}</p>
                    {config.change_note && <p>Note: {config.change_note}</p>}
                  </div>
                )}

                {/* Publish button */}
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
                  <textarea
                    rows={2}
                    placeholder="Change note (reason for this update)…"
                    value={configNote}
                    onChange={e => setConfigNote(e.target.value)}
                    disabled={!isAdmin}
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm resize-none disabled:opacity-40"
                  />
                  {configError   && <p className="text-red-400 text-xs">{configError}</p>}
                  {configSuccess && <p className="text-green-400 text-xs">{configSuccess}</p>}
                  <button
                    onClick={handlePublishConfig}
                    disabled={!isAdmin}
                    className="w-full py-2.5 rounded-lg font-medium text-sm bg-gradient-to-r from-violet-700 to-violet-600 hover:from-violet-600 hover:to-violet-500 text-white shadow-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Publish New Config Version
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ─────────────────────── AUDIT TAB ─────────────────────── */}
      {tab === 'audit' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-xl">
          <div className="flex items-center justify-between mb-5">
            <SectionHeader
              icon={<History className="w-5 h-5 text-teal-400" />}
              title="Audit Trail"
              subtitle="Immutable log of all rule management changes"
            />
            <button onClick={loadAudit} className="p-2 hover:text-gray-200 text-gray-500 transition-colors">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
          {auditLog.length === 0 ? (
            <p className="text-gray-600 text-sm">No audit events yet.</p>
          ) : (
            <div className="space-y-2">
              {auditLog.map(entry => (
                <div key={entry.audit_id} className="flex items-start gap-4 p-3 rounded-lg bg-gray-950/50 border border-gray-800 text-sm">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium shrink-0 ${
                    entry.action === 'CREATE' ? 'bg-green-900/50 text-green-400' :
                    entry.action === 'DEACTIVATE' ? 'bg-red-900/50 text-red-400' :
                    entry.action === 'PUBLISH' ? 'bg-violet-900/50 text-violet-400' :
                    'bg-blue-900/50 text-blue-400'
                  }`}>
                    {entry.action}
                  </span>
                  <div className="flex-1 min-w-0">
                    {entry.new_value && (
                      <p className="text-gray-300 truncate">
                        {entry.new_value.classification_code
                          ? `${entry.new_value.classification_code} / ${entry.new_value.attribute}`
                          : `Config v${entry.new_value.version}`}
                      </p>
                    )}
                    <p className="text-gray-600 text-xs mt-0.5">
                      {entry.actor_id || 'system'} · {new Date(entry.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
