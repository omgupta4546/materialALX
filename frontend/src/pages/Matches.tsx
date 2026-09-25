import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ShieldAlert, CheckCircle2, XCircle, Wrench, AlertTriangle,
  RefreshCw, X,
  Bot, UserCheck, Sparkles, Scale, Zap, Info
} from 'lucide-react';
import {
  getMatchesFn, getMatchDetailFn, approveMatchFn, rejectMatchFn, engineeringReviewFn,
  type MatchSummary, type MatchesParams, type MaterialSnapshot, type ReviewActionRequest
} from '../api/matches';
import { cn } from '../components/common/MetricCard';

// ══════════════════════════════════════════════════════════
// SHARED PRIMITIVES
// ══════════════════════════════════════════════════════════

const ReviewBadge: React.FC<{ status: string | null }> = ({ status }) => {
  const cfg: Record<string, string> = {
    PENDING:   'bg-amber-50 text-amber-700 border-amber-200',
    APPROVED:  'bg-green-50 text-green-700 border-green-200',
    REJECTED:  'bg-red-50 text-red-600 border-red-200',
    ESCALATED: 'bg-blue-50 text-blue-700 border-blue-200',
  };
  const label = status === 'ESCALATED' ? 'ENG REVIEW' : (status ?? 'PENDING');
  return (
    <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border', cfg[status ?? 'PENDING'] ?? cfg.PENDING)}>
      {label.replace('_', ' ')}
    </span>
  );
};

const AIBadge: React.FC<{ rec: string }> = ({ rec }) => {
  const cfg: Record<string, { cls: string; icon: React.ReactNode }> = {
    APPROVE: { cls: 'text-green-700 bg-green-50 border-green-200', icon: <CheckCircle2 size={11} /> },
    REJECT:  { cls: 'text-red-600 bg-red-50 border-red-200',       icon: <XCircle size={11} /> },
    REVIEW:  { cls: 'text-amber-700 bg-amber-50 border-amber-200', icon: <AlertTriangle size={11} /> },
  };
  const { cls, icon } = cfg[rec] ?? cfg.REVIEW;
  return (
    <span className={cn('inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border', cls)}>
      <Bot size={10} /> AI: {icon} {rec}
    </span>
  );
};

const RiskBadge: React.FC<{ level: string }> = ({ level }) => {
  const cfg: Record<string, string> = {
    LOW:      'text-green-700',
    MEDIUM:   'text-amber-600',
    HIGH:     'text-orange-600',
    CRITICAL: 'text-red-600 animate-pulse',
  };
  return <span className={cn('font-bold text-xs uppercase tracking-wide', cfg[level] ?? 'text-muted-foreground')}>{level}</span>;
};

// Confidence score pill badge
const ConfidencePill: React.FC<{ score: number | null }> = ({ score }) => {
  if (score === null) return <span className="text-muted-foreground text-xs">—</span>;
  const pct = Math.round(score * 100);
  const cls = pct >= 85
    ? 'bg-green-50 text-green-700 border-green-200'
    : pct >= 65
    ? 'bg-amber-50 text-amber-700 border-amber-200'
    : 'bg-red-50 text-red-600 border-red-200';
  return (
    <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold tabular-nums border', cls)}>
      {pct}%
    </span>
  );
};

const ScoreBar: React.FC<{ label: string; value: number | null; icon: React.ReactNode }> = ({ label, value, icon }) => {
  const pct = value !== null ? Math.round(value * 100) : 0;
  const color = pct >= 85 ? 'bg-green-500' : pct >= 65 ? 'bg-amber-400' : 'bg-red-500';
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="flex items-center gap-1">{icon} {label}</span>
        <span className={cn('font-mono font-semibold', pct >= 85 ? 'text-green-400' : pct >= 65 ? 'text-amber-400' : 'text-red-400')}>
          {value !== null ? `${pct}%` : '—'}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div className={cn('h-full rounded-full transition-all duration-700', color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════
// MATERIAL SNAPSHOT CARD
// ══════════════════════════════════════════════════════════

const MatCard: React.FC<{ mat: MaterialSnapshot; label: string; highlightDiffs?: Record<string, string> }> = ({ mat, label, highlightDiffs = {} }) => (
  <div className="card overflow-hidden flex-1 min-w-0">
    <div className="px-4 py-2.5 bg-muted/40 border-b border-border flex items-center justify-between">
      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{label}</span>
      <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full font-semibold">{mat.cpse_id}</span>
    </div>
    <div className="p-4 space-y-3 text-sm">
      <DataRow label="Code" value={mat.legacy_material_code} mono />
      <DataRow label="Description" value={mat.raw_description} />
      <DataRow label="Normalized" value={mat.normalized_description} emphasized />
      <DataRow label="Manufacturer" value={mat.manufacturer} diff={highlightDiffs.manufacturer} />
      <DataRow label="MPN" value={mat.manufacturer_part_number} diff={highlightDiffs.manufacturer_part_number} mono />
      <DataRow label="UOM" value={mat.raw_uom} diff={highlightDiffs.uom} mono />
      <DataRow label="Category" value={mat.classification_id} />
    </div>
  </div>
);

const DataRow: React.FC<{ label: string; value: string | null | undefined; mono?: boolean; emphasized?: boolean; diff?: string }> = ({ label, value, mono, emphasized, diff }) => (
  <div className={cn('flex items-start gap-3', diff && 'rounded px-2 py-1 -mx-2 bg-red-500/5 border border-red-500/10')}>
    <span className="text-muted-foreground shrink-0 w-24 text-xs pt-0.5">{label}</span>
    <span className={cn('break-all', mono && 'font-mono text-xs', emphasized && 'font-medium text-foreground')}>
      {value ?? <span className="text-muted-foreground italic text-xs">—</span>}
    </span>
  </div>
);

// ══════════════════════════════════════════════════════════
// DETAIL DRAWER
// ══════════════════════════════════════════════════════════

const MatchDetailDrawer: React.FC<{ matchId: string; onClose: () => void; onAction: () => void }> = ({ matchId, onClose, onAction }) => {
  const qc = useQueryClient();
  const [notes, setNotes] = useState('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['match-detail', matchId],
    queryFn: () => getMatchDetailFn(matchId),
  });

  const afterAction = () => {
    qc.invalidateQueries({ queryKey: ['match-detail', matchId] });
    qc.invalidateQueries({ queryKey: ['matches'] });
    setActionLoading(null);
    onAction();
  };

  const doAction = async (type: 'approve' | 'reject' | 'engineering-review') => {
    setActionLoading(type);
    const payload: ReviewActionRequest = { comment: notes, reviewer_id: 'DEMO_USER' };
    try {
      if (type === 'approve') await approveMatchFn(matchId, payload);
      else if (type === 'reject') await rejectMatchFn(matchId, payload);
      else await engineeringReviewFn(matchId, payload);
      afterAction();
    } catch { setActionLoading(null); }
  };

  // Compute attribute diffs between mat_a and mat_b
  const attrDiffs: Record<string, string> = {};
  if (data?.material_a && data?.material_b) {
    if (data.material_a.manufacturer !== data.material_b.manufacturer) attrDiffs.manufacturer = 'diff';
    if (data.material_a.raw_uom !== data.material_b.raw_uom) attrDiffs.uom = 'diff';
    if (data.material_a.manufacturer_part_number !== data.material_b.manufacturer_part_number) attrDiffs.manufacturer_part_number = 'diff';
  }

  const currentStatus = data?.decision;

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="w-[900px] max-w-[95vw] bg-card border-l border-border flex flex-col overflow-hidden shadow-2xl">
        {/* Topbar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0 bg-card/80 backdrop-blur">
          <div className="flex items-center gap-3">
            <Scale size={18} className="text-primary" />
            <h2 className="font-bold text-lg">Match Review</h2>
            {data && <ReviewBadge status={data.decision || 'PENDING'} />}
            {data && <AIBadge rec={data.recommendation || 'REVIEW'} />}
          </div>
          <button onClick={onClose} className="p-1.5 rounded-md hover:bg-accent transition-colors"><X size={18} /></button>
        </div>

        <div className="overflow-y-auto flex-1">
          {isLoading ? (
            <div className="flex items-center justify-center h-60 text-muted-foreground">
              <RefreshCw size={20} className="animate-spin mr-2" /> Loading match details…
            </div>
          ) : data ? (
            <div className="p-6 space-y-6">

              {/* Score Breakdown */}
              <div className="card p-5 space-y-4">
                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <Bot size={14} /> AI Scoring Breakdown
                </h3>
                <div className="grid grid-cols-3 gap-4">
                  <ScoreBar label="Semantic Score" value={data.semantic_score} icon={<Sparkles size={11} />} />
                  <ScoreBar label="Attribute Score" value={data.attribute_score} icon={<Zap size={11} />} />
                  <ScoreBar label="Rule Score" value={data.rule_score} icon={<ShieldAlert size={11} />} />
                </div>
                <div className="flex items-center gap-4 pt-2 border-t border-border px-4 pb-4">
                  <div className="flex flex-col gap-1">
                    <span className="text-xs text-muted-foreground">UOM Match</span>
                    <span className="font-semibold text-sm flex items-center gap-1">
                      {data.material_a?.raw_uom === data.material_b?.raw_uom
                        ? <><CheckCircle2 size={13} className="text-green-500" /> Yes</>
                        : <><XCircle size={13} className="text-red-500" /> No</>}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-xs text-muted-foreground">Review Status</span>
                    <span><ReviewBadge status={data.decision || 'PENDING'} /></span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <p className="text-xs text-muted-foreground">Match Type</p>
                    <p className="font-semibold text-sm">{data.match_type}</p>
                  </div>
                  <div className="flex flex-col gap-1">
                    <p className="text-xs text-muted-foreground">Final Confidence</p>
                    <p className={cn('font-bold text-lg', (data.final_score ?? 0) >= 0.9 ? 'text-green-400' : (data.final_score ?? 0) >= 0.7 ? 'text-amber-400' : 'text-red-400')}>
                      {data.final_score !== null && data.final_score !== undefined ? `${Math.round((data.final_score ?? 0) * 100)}%` : '—'}
                    </p>
                  </div>
                  <div className="flex flex-col gap-1">
                    <p className="text-xs text-muted-foreground">Risk Level</p>
                    <RiskBadge level={data.risk_level} />
                  </div>
                </div>
              </div>

              {/* Material Comparison */}
              <div>
                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
                  <Scale size={14} /> Material Comparison
                </h3>
                <div className="flex gap-4">
                  {data.material_a ? <MatCard mat={data.material_a} label="Material A (Query)" highlightDiffs={attrDiffs} /> : <NullCard label="Material A" />}
                  <div className="flex flex-col items-center justify-center shrink-0">
                    <div className="w-px h-full bg-border" />
                    <span className="text-xs font-bold text-muted-foreground bg-card px-2 py-1 border border-border rounded my-2">VS</span>
                    <div className="w-px h-full bg-border" />
                  </div>
                  {data.material_b ? <MatCard mat={data.material_b} label="Material B (Candidate)" highlightDiffs={attrDiffs} /> : <NullCard label="Material B" />}
                </div>
              </div>

              {/* Critical Conflicts */}
              {data.conflicts && Object.keys(data.conflicts).length > 0 && (
                <div className="glass rounded-xl overflow-hidden border-red-500/30">
                  <div className="p-4 bg-red-500/5">
                    <h3 className="text-sm font-semibold text-red-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                      <ShieldAlert size={14} className="text-red-400" /> Critical Conflicts
                    </h3>
                    <ul className="space-y-2">
                      {Object.keys(data.conflicts).map((c, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-red-400/90">
                          <XCircle size={14} className="mt-0.5 shrink-0" />
                          <span>{data.conflicts[c]}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* AI Recommendation Panel */}
            <div className={cn(
              'border rounded-xl overflow-hidden shadow-sm relative overflow-visible',
              data.decision != null ? 'opacity-60 grayscale' : 'border-primary/30'
            )}>
              <div className="bg-primary/5 px-4 py-3 border-b border-primary/10 flex items-center gap-2">
                <Sparkles size={16} className="text-primary" />
                <h3 className="font-semibold text-sm text-primary">AI Recommendation</h3>
              </div>
              <div className="p-5 flex items-start gap-4">
                <div className="flex-1">
                  <p className="text-lg font-medium leading-snug">{data.recommendation}</p>
                </div>
              </div>
            </div>

              {/* AI Explanation / Evidence */}
              {((data.positive_evidence && Object.keys(data.positive_evidence).length > 0) || (data.negative_evidence && Object.keys(data.negative_evidence).length > 0)) && (
                <div className="glass rounded-xl overflow-hidden">
                  <div className="px-4 py-2.5 bg-muted/30 border-b border-border flex items-center justify-between">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2"><Sparkles size={13} /> AI Reasoning & Evidence</span>
                  </div>
                  <div className="p-4 text-sm leading-relaxed whitespace-pre-wrap">
                    <div className="mb-2 font-semibold">Positive Evidence:</div>
                    {data.positive_evidence && Object.keys(data.positive_evidence).length > 0 ? (
                      <ul className="list-disc pl-5 mb-4">
                        {Object.values(data.positive_evidence).map((e, i) => <li key={i}>{e as string}</li>)}
                      </ul>
                    ) : <p className="mb-4">None.</p>}
                    
                    <div className="mb-2 font-semibold">Negative Evidence:</div>
                    {data.negative_evidence && Object.keys(data.negative_evidence).length > 0 ? (
                      <ul className="list-disc pl-5">
                        {Object.values(data.negative_evidence).map((e, i) => <li key={i}>{e as string}</li>)}
                      </ul>
                    ) : <p>None.</p>}
                  </div>
                </div>
              )}

              {/* Critical Warnings */}
              {data.conflicts && Object.keys(data.conflicts).length > 0 && (
                <div className="card p-4 border border-red-200 bg-red-50/60">
                  <h4 className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <ShieldAlert size={12} /> Critical Attribute Warnings
                  </h4>
                  <div className="space-y-2">
                    {Object.keys(data.conflicts).map((k, i) => (
                      <div key={i} className="flex items-start gap-3 text-sm border-b border-red-500/10 pb-2">
                        <div className="flex-1">
                          <p className="font-medium text-red-400">{data.conflicts[k]}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Review History */}
              {data.review_history && data.review_history.length > 0 && (
                <div className="card p-4">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
                    <UserCheck size={12} /> Human Review History
                  </h4>
                  <div className="space-y-2">
                    {data.review_history.map((r) => (
                      <div key={r.approval_id} className="flex items-center gap-3 text-sm">
                        <ReviewBadge status={r.decision} />
                        <span className="text-muted-foreground text-xs">{r.reviewer_id ?? 'System'}</span>
                        <span className="text-muted-foreground text-xs ml-auto">{new Date(r.created_at).toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Action Footer */}
        <div className="px-6 py-4 border-t border-border shrink-0 bg-card/80 backdrop-blur space-y-3">
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Optional review notes…"
            rows={2}
            className="w-full p-2 rounded-md border border-border bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
          <div className="flex gap-2 flex-wrap">
            <ActionBtn
              label="Approve" icon={<CheckCircle2 size={14} />}
              cls="bg-green-600 hover:bg-green-500 text-white"
              loading={actionLoading === 'approve'}
              disabled={!!actionLoading || currentStatus === 'APPROVED'}
              onClick={() => doAction('approve')}
            />
            <ActionBtn
              label="Reject" icon={<XCircle size={14} />}
              cls="bg-red-600 hover:bg-red-500 text-white"
              loading={actionLoading === 'reject'}
              disabled={!!actionLoading || currentStatus === 'REJECTED'}
              onClick={() => doAction('reject')}
            />
            <ActionBtn
              label="Engineering Review" icon={<Wrench size={14} />}
              cls="bg-blue-600 hover:bg-blue-500 text-white"
              loading={actionLoading === 'engineering-review'}
              disabled={!!actionLoading || currentStatus === 'ESCALATED'}
              onClick={() => doAction('engineering-review')}
            />
          </div>
          <p className="text-xs text-muted-foreground flex items-center gap-1">
            <Info size={10} /> Human decisions are recorded separately from AI recommendations and are immutable.
          </p>
        </div>
      </div>
    </div>
  );
};

const NullCard: React.FC<{ label: string }> = ({ label }) => (
  <div className="card flex-1 flex items-center justify-center p-8 text-muted-foreground text-sm italic">{label} not available</div>
);

const ActionBtn: React.FC<{
  label: string; icon: React.ReactNode; cls: string;
  loading: boolean; disabled: boolean; onClick: () => void;
}> = ({ label, icon, cls, loading, disabled, onClick }) => (
  <button
    onClick={onClick}
    disabled={disabled || loading}
    className={cn('flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed', cls)}
  >
    {loading ? <RefreshCw size={13} className="animate-spin" /> : icon}
    {label}
  </button>
);

// ══════════════════════════════════════════════════════════
// REVIEW QUEUE TABLE
// ══════════════════════════════════════════════════════════

const MATCH_TYPE_COLORS: Record<string, string> = {
  EXACT_DUPLICATE:             'text-green-400',
  NEAR_DUPLICATE:              'text-blue-400',
  FUNCTIONALLY_EQUIVALENT:     'text-purple-400',
  RELATED:                     'text-cyan-400',
  NOT_EQUIVALENT:              'text-red-400',
  REQUIRES_ENGINEERING_REVIEW: 'text-orange-400',
};

const MATCH_TYPE_LABELS: Record<string, string> = {
  EXACT_DUPLICATE:             'Exact Duplicate',
  NEAR_DUPLICATE:              'Near Duplicate',
  FUNCTIONALLY_EQUIVALENT:     'Functionally Equiv.',
  RELATED:                     'Related',
  NOT_EQUIVALENT:              'Not Equivalent',
  REQUIRES_ENGINEERING_REVIEW: 'Needs Eng. Review',
};

export const Matches: React.FC = () => {
  const [params, setParams] = useState<MatchesParams>({ limit: 50, offset: 0 });
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['matches', params],
    queryFn: () => getMatchesFn(params),
    placeholderData: (prev) => prev,
  });

  const setParam = (key: keyof MatchesParams, value: any) =>
    setParams(p => ({ ...p, [key]: value || undefined, offset: 0 }));

  const totalPages = data ? Math.ceil(data.total / (params.limit ?? 50)) : 1;
  const currentPage = Math.floor((params.offset ?? 0) / (params.limit ?? 50)) + 1;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading flex items-center gap-2">
            <Scale size={22} className="text-primary" /> Match Review Queue
          </h1>
          {data && (
            <p className="text-sm text-muted-foreground mt-0.5">
              {data.total.toLocaleString()} matches · Review pending items to build the National Material Catalog
            </p>
          )}
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-primary border border-border rounded-lg px-3 py-2 hover:border-primary/40 hover:bg-primary/5 transition-all"
        >
          <RefreshCw size={13} className={cn(isFetching && 'animate-spin text-primary')} />
          Refresh
        </button>
      </div>

      {/* ── Stat Summary Cards ── */}
      {data && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            {
              label: 'Total Matches',
              value: data.total,
              color: '#0F5B3D',
              chipCls: 'kpi-chip kpi-chip-green',
              icon: <Scale size={20} />,
            },
            {
              label: 'Pending Review',
              value: data.items.filter((m: MatchSummary) => !m.decision || m.decision === 'PENDING').length,
              color: '#92610a',
              chipCls: 'kpi-chip kpi-chip-amber',
              icon: <AlertTriangle size={20} />,
              note: 'in this page',
            },
            {
              label: 'Approved',
              value: data.items.filter((m: MatchSummary) => m.decision === 'APPROVED').length,
              color: '#0F5B3D',
              chipCls: 'kpi-chip kpi-chip-green',
              icon: <CheckCircle2 size={20} />,
              note: 'in this page',
            },
            {
              label: 'Critical Conflicts',
              value: data.items.filter((m: MatchSummary) => m.requires_human_review).length,
              color: '#ef4444',
              chipCls: 'kpi-chip kpi-chip-red',
              icon: <ShieldAlert size={20} />,
              note: 'in this page',
            },
          ].map((s) => (
            <div key={s.label} className="card p-4 flex items-start gap-3">
              <div className={s.chipCls}>{s.icon}</div>
              <div className="min-w-0">
                <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-1">{s.label}</p>
                <p className="text-2xl font-bold tabular-nums leading-tight" style={{ color: s.color }}>
                  {s.value.toLocaleString()}
                </p>
                {s.note && <p className="text-[10px] text-muted-foreground mt-0.5">{s.note}</p>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Filter strip */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Review Status</label>
            <select className="p-2 rounded-md border border-border bg-background text-sm min-w-[160px]" onChange={e => setParam('decision', e.target.value as any)}>
              <option value="">All Statuses</option>
              <option value="PENDING">Pending (no decision)</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
              <option value="ESCALATED">Engineering Review</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Match Type</label>
            <select className="p-2 rounded-md border border-border bg-background text-sm min-w-[180px]" onChange={e => setParam('match_type', e.target.value as any)}>
              <option value="">All Types</option>
              <option value="EXACT_DUPLICATE">Exact Duplicate</option>
              <option value="NEAR_DUPLICATE">Near Duplicate</option>
              <option value="FUNCTIONALLY_EQUIVALENT">Functionally Equiv.</option>
              <option value="RELATED">Related</option>
              <option value="NOT_EQUIVALENT">Not Equivalent</option>
              <option value="REQUIRES_ENGINEERING_REVIEW">Needs Eng. Review</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Min Confidence</label>
            <select className="p-2 rounded-md border border-border bg-background text-sm" onChange={e => setParam('min_score', e.target.value ? parseFloat(e.target.value) : undefined)}>
              <option value="">Any</option>
              <option value="0.9">≥ 90%</option>
              <option value="0.75">≥ 75%</option>
              <option value="0.5">≥ 50%</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Critical Conflict</label>
            <select className="p-2 rounded-md border border-border bg-background text-sm" onChange={e => setParam('requires_review', e.target.value === '' ? undefined : e.target.value === 'true')}>
              <option value="">All</option>
              <option value="true">Has Conflict</option>
              <option value="false">No Conflict</option>
            </select>
          </div>
        </div>
      </div>

      {/* Queue Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 border-b border-border">
              <tr>
                {['Match ID', 'CPSE A', 'Material A', 'CPSE B', 'Material B', 'Match Type', 'Confidence', 'Conflict', 'AI Rec.', 'Status', 'Action'].map(h => (
                  <th key={h} className="p-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={10} className="p-12 text-center text-muted-foreground"><RefreshCw size={20} className="animate-spin inline mr-2" />Loading matches…</td></tr>
              ) : data?.items.length === 0 ? (
                <tr><td colSpan={10} className="p-12 text-center text-muted-foreground">
                  <Scale size={32} className="mx-auto mb-3 opacity-30" />
                  <p>No matches found.</p>
                  <p className="text-xs mt-1">Run the AI batch-process job to generate match candidates.</p>
                </td></tr>
              ) : (
                data?.items.map((m: MatchSummary) => (
                  <tr
                    key={m.match_id}
                    onClick={() => setSelectedId(m.match_id)}
                    className="border-b border-border/50 hover:bg-primary/3 cursor-pointer transition-colors group"
                  >
                    <td className="p-3 font-mono text-xs text-muted-foreground">{m.match_id.slice(0, 8)}…</td>
                    <td className="p-3"><span className="text-xs bg-primary/8 text-primary px-2 py-0.5 rounded-full font-semibold">—</span></td>
                    <td className="p-3 max-w-[180px]">
                      <p className="font-mono text-xs text-primary">{m.material_a_id.slice(0,8)}…</p>
                      <p className="text-muted-foreground truncate text-xs">Material A</p>
                    </td>
                    <td className="p-3"><span className="text-xs bg-primary/8 text-primary px-2 py-0.5 rounded-full font-semibold">—</span></td>
                    <td className="p-3 max-w-[180px]">
                      <p className="font-mono text-xs text-primary">{m.material_b_id.slice(0,8)}…</p>
                      <p className="text-muted-foreground truncate text-xs">Material B</p>
                    </td>
                    <td className="p-3">
                      <span className={cn('text-xs font-semibold', MATCH_TYPE_COLORS[m.match_type ?? ''] ?? 'text-muted-foreground')}>
                        {m.match_type ? (MATCH_TYPE_LABELS[m.match_type] ?? m.match_type) : '—'}
                      </span>
                    </td>
                    {/* Confidence pill */}
                    <td className="p-3">
                      <ConfidencePill score={m.final_score} />
                    </td>
                    <td className="p-3">
                      {m.requires_human_review
                        ? <span className="flex items-center gap-1 text-red-600 text-xs font-semibold"><ShieldAlert size={12} /> YES</span>
                        : <span className="text-muted-foreground text-xs">—</span>}
                    </td>
                    <td className="p-3"><AIBadge rec={m.recommendation ?? 'REVIEW'} /></td>
                    <td className="p-3"><ReviewBadge status={m.decision ?? 'PENDING'} /></td>
                    {/* Review action button */}
                    <td className="p-3" onClick={e => e.stopPropagation()}>
                      <button
                        onClick={() => setSelectedId(m.match_id)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all hover:-translate-y-px"
                        style={{
                          color: 'hsl(155,73%,21%)',
                          borderColor: 'hsl(155 73% 21% / 0.35)',
                          background: 'hsl(155 73% 21% / 0.04)',
                        }}
                      >
                        <Scale size={12} />
                        Review
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && data.total > 0 && (
          <div className="px-4 py-3 border-t border-border flex items-center justify-between text-sm text-muted-foreground">
            <span>Showing {(params.offset ?? 0) + 1}–{Math.min((params.offset ?? 0) + (params.limit ?? 50), data.total)} of {data.total.toLocaleString()}</span>
            <div className="flex items-center gap-2">
              <button disabled={currentPage <= 1} onClick={() => setParams(p => ({ ...p, offset: Math.max(0, (p.offset ?? 0) - (p.limit ?? 50)) }))} className="px-3 py-1.5 rounded border border-border hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed transition-colors">Previous</button>
              <span className="px-3 py-1.5 rounded border border-border bg-primary/10 text-primary font-medium">{currentPage} / {totalPages}</span>
              <button disabled={!data.has_more} onClick={() => setParams(p => ({ ...p, offset: (p.offset ?? 0) + (p.limit ?? 50) }))} className="px-3 py-1.5 rounded border border-border hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed transition-colors">Next</button>
            </div>
          </div>
        )}
      </div>

      {/* Detail Drawer */}
      {selectedId && (
        <MatchDetailDrawer
          matchId={selectedId}
          onClose={() => setSelectedId(null)}
          onAction={() => {}} // Queue refetch handled via invalidateQueries
        />
      )}
    </div>
  );
};
