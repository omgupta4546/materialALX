import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, RadialBarChart, RadialBar
} from 'recharts';
import {
  Package, Cpu, Copy, Shuffle, CheckCircle2, ShieldAlert,
  Wrench, TrendingUp, Upload, Clock, RefreshCw, AlertTriangle,
  Database, Star, Zap, Activity
} from 'lucide-react';
import { getDashboardFn, type DashboardPayload } from '../api/analytics';
import { cn } from '../components/common/MetricCard';

// ══════════════════════════════════════════════════════════════
// CONSTANTS
// ══════════════════════════════════════════════════════════════

const PALETTE = ['#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#14b8a6'];
const CHART_THEME = {
  background: 'transparent',
  text: '#94a3b8',
  grid: 'rgba(148,163,184,0.08)',
};

// ══════════════════════════════════════════════════════════════
// SHARED COMPONENTS
// ══════════════════════════════════════════════════════════════

const CardShell: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className }) => (
  <div className={cn('glass rounded-xl overflow-hidden', className)}>{children}</div>
);

const CardHeader: React.FC<{ icon: React.ReactNode; title: string; subtitle?: string }> = ({ icon, title, subtitle }) => (
  <div className="px-5 py-4 border-b border-border flex items-start justify-between">
    <div>
      <h3 className="font-semibold text-sm flex items-center gap-2">{icon}{title}</h3>
      {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
    </div>
  </div>
);

// KPI Card
const KpiCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: number | string;
  sub?: string;
  trend?: 'up' | 'down' | 'neutral';
  color?: string;
  alert?: boolean;
}> = ({ icon, label, value, sub, color = 'text-primary', alert }) => (
  <CardShell>
    <div className={cn('p-5 relative overflow-hidden', alert && 'border-l-2 border-red-500')}>
      <div className={cn('absolute -right-4 -top-4 w-20 h-20 rounded-full opacity-5', alert ? 'bg-red-500' : 'bg-primary')} />
      <div className={cn('inline-flex p-2.5 rounded-lg mb-3', alert ? 'bg-red-500/10 text-red-400' : 'bg-primary/10 text-primary')}>{icon}</div>
      <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{label}</p>
      <p className={cn('text-3xl font-bold tabular-nums', alert ? 'text-red-400' : color)}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  </CardShell>
);

// Quality Gauge
const QualityGauge: React.FC<{ score: number }> = ({ score }) => {
  const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';
  const label = score >= 80 ? 'Excellent' : score >= 60 ? 'Good' : 'Needs Work';
  const data = [{ name: 'Score', value: score, fill: color }, { name: 'Gap', value: 100 - score, fill: 'transparent' }];
  return (
    <CardShell>
      <div className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <Star size={15} className="text-primary" />
          <span className="text-sm font-semibold">Data Quality Score</span>
        </div>
        <div className="flex items-center justify-center">
          <div className="relative">
            <RadialBarChart width={160} height={160} cx={80} cy={80} innerRadius={50} outerRadius={75} data={data} startAngle={180} endAngle={0}>
              <RadialBar dataKey="value" cornerRadius={8} background={false} />
            </RadialBarChart>
            <div className="absolute inset-0 flex flex-col items-center justify-center" style={{ top: 20 }}>
              <p className="text-3xl font-bold" style={{ color }}>{score.toFixed(1)}</p>
              <p className="text-xs text-muted-foreground">{label}</p>
            </div>
          </div>
        </div>
      </div>
    </CardShell>
  );
};

// Custom Tooltip
const ChartTooltip: React.FC<{ active?: boolean; payload?: any[]; label?: any; formatter?: (v: any) => string }> = ({ active, payload, label, formatter }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass border border-border rounded-lg px-3 py-2 text-xs shadow-xl">
      {label && <p className="font-semibold mb-1">{label}</p>}
      {payload.map((p: any, i: number) => (
        <p key={i} style={{ color: p.color || p.fill }}>
          {p.name}: <span className="font-bold">{formatter ? formatter(p.value) : p.value?.toLocaleString()}</span>
        </p>
      ))}
    </div>
  );
};

// ── Status/event badges ─────────────────────────────────────────────────────
const StatusPill: React.FC<{ status: string }> = ({ status }) => {
  const cfg: Record<string, string> = {
    COMPLETED:        'bg-green-500/15 text-green-400',
    APPROVED:         'bg-green-500/15 text-green-400',
    RUNNING:          'bg-blue-500/15 text-blue-400',
    PENDING:          'bg-amber-500/15 text-amber-400',
    FAILED:           'bg-red-500/15 text-red-400',
    REJECTED:         'bg-red-500/15 text-red-400',
    ENG_REVIEW:       'bg-purple-500/15 text-purple-400',
    NEEDS_CORRECTION: 'bg-orange-500/15 text-orange-400',
  };
  return (
    <span className={cn('px-1.5 py-0.5 rounded text-xs font-semibold', cfg[status] ?? 'bg-muted text-muted-foreground')}>
      {status}
    </span>
  );
};

// ══════════════════════════════════════════════════════════════
// EMPTY / LOADING STATES
// ══════════════════════════════════════════════════════════════

const ChartEmpty: React.FC<{ height?: number }> = ({ height = 200 }) => (
  <div className="flex flex-col items-center justify-center text-muted-foreground" style={{ height }}>
    <Activity size={24} className="mb-2 opacity-30" />
    <p className="text-xs">No data yet. Upload materials to populate.</p>
  </div>
);

// ══════════════════════════════════════════════════════════════
// DASHBOARD
// ══════════════════════════════════════════════════════════════

export const Dashboard: React.FC = () => {
  const { data, isLoading, isFetching, refetch } = useQuery<DashboardPayload>({
    queryKey: ['dashboard'],
    queryFn: getDashboardFn,
    refetchInterval: 30_000, // auto-refresh every 30s
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96 text-muted-foreground">
        <RefreshCw size={24} className="animate-spin mr-3" />
        <span>Loading dashboard from live backend data…</span>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-muted-foreground gap-3">
        <AlertTriangle size={32} className="text-amber-400" />
        <p>Could not connect to backend analytics API.</p>
        <button onClick={() => refetch()} className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm">Retry</button>
      </div>
    );
  }

  const { kpis, charts, recent } = data;

  return (
    <div className="space-y-6 pb-10">

      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Platform Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Live analytics from backend — all metrics sourced from database</p>
        </div>
        <button onClick={() => refetch()} title="Refresh" className="p-2 rounded-md border border-border hover:bg-accent transition-colors">
          <RefreshCw size={16} className={cn(isFetching && 'animate-spin')} />
        </button>
      </div>

      {/* ── KPI Row 1: Core Pipeline ─────────────────────────────── */}
      <div>
        <p className="text-xs text-muted-foreground uppercase tracking-widest font-semibold mb-3 pl-1">Pipeline Status</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard icon={<Package size={18} />} label="Source Materials" value={kpis.total_source_materials} sub="Total ingested across all CPSEs" />
          <KpiCard
            icon={<Cpu size={18} />}
            label="Normalized"
            value={kpis.normalized_materials}
            sub={`${kpis.normalization_pct}% of source catalog`}
            color={kpis.normalization_pct >= 80 ? 'text-green-400' : 'text-amber-400'}
          />
          <KpiCard icon={<Copy size={18} />} label="Duplicate Candidates" value={kpis.duplicate_candidates} sub="Near-duplicate match results" />
          <KpiCard icon={<Shuffle size={18} />} label="Functional Equiv." value={kpis.functional_equivalents} sub="Cross-CPSE functional matches" />
        </div>
      </div>

      {/* ── KPI Row 2: Approval & Quality ────────────────────────── */}
      <div>
        <p className="text-xs text-muted-foreground uppercase tracking-widest font-semibold mb-3 pl-1">Approvals & Quality</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard icon={<Clock size={18} />} label="Pending Approvals" value={kpis.pending_approvals} sub="Awaiting human review" color={kpis.pending_approvals > 0 ? 'text-amber-400' : 'text-green-400'} />
          <KpiCard icon={<CheckCircle2 size={18} />} label="Approved Mappings" value={kpis.approved_mappings} sub={`${kpis.mapping_pct}% of source mapped`} color="text-green-400" />
          <KpiCard icon={<ShieldAlert size={18} />} label="High-Risk Matches" value={kpis.high_risk_matches} sub="Critical conflict flag" alert={kpis.high_risk_matches > 0} />
          <KpiCard icon={<Wrench size={18} />} label="Engineering Reviews" value={kpis.engineering_reviews} sub="Flagged for engineer sign-off" color={kpis.engineering_reviews > 0 ? 'text-blue-400' : 'text-foreground'} />
        </div>
      </div>

      {/* ── Quality Gauge + Top stats ─────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <QualityGauge score={kpis.data_quality_score} />
        <KpiCard icon={<Database size={18} />} label="Total Matches" value={kpis.total_matches} sub="AI match candidates generated" />
        <KpiCard icon={<CheckCircle2 size={18} />} label="Total Mapped" value={kpis.total_mapped} sub="Source → National mappings" />
        <KpiCard icon={<Zap size={18} />} label="National Codes" value={kpis.approved_mappings} sub="Golden records in catalog" />
      </div>

      {/* ── Chart Row 1: By CPSE + Upload Status ─────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Materials by CPSE */}
        <CardShell>
          <CardHeader icon={<Package size={15} className="text-primary" />} title="Materials by CPSE" subtitle="Source catalog distribution across organizations" />
          <div className="p-4">
            {charts.materials_by_cpse.length === 0 ? <ChartEmpty /> : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={charts.materials_by_cpse} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} />
                  <XAxis dataKey="cpse" tick={{ fill: CHART_THEME.text, fontSize: 11 }} />
                  <YAxis tick={{ fill: CHART_THEME.text, fontSize: 11 }} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="count" name="Materials" radius={[4, 4, 0, 0]}>
                    {charts.materials_by_cpse.map((_, i) => (
                      <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </CardShell>

        {/* Confidence Distribution */}
        <CardShell>
          <CardHeader icon={<Activity size={15} className="text-primary" />} title="Confidence Distribution" subtitle="Mapping confidence bands across all records" />
          <div className="p-4">
            {charts.confidence_distribution.every(d => d.count === 0) ? <ChartEmpty /> : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={charts.confidence_distribution} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} />
                  <XAxis dataKey="range" tick={{ fill: CHART_THEME.text, fontSize: 11 }} />
                  <YAxis tick={{ fill: CHART_THEME.text, fontSize: 11 }} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="count" name="Mappings" radius={[4, 4, 0, 0]}>
                    {charts.confidence_distribution.map((_, i) => (
                      <Cell key={i} fill={['#10b981', '#06b6d4', '#f59e0b', '#ef4444'][i % 4]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </CardShell>
      </div>

      {/* ── Chart Row 2: Classification Coverage + Procurement ────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Classification Coverage */}
        <CardShell>
          <CardHeader icon={<TrendingUp size={15} className="text-primary" />} title="Classification Coverage" subtitle="Normalized materials by category" />
          <div className="p-4 flex items-center gap-4">
            {charts.classification_coverage.length === 0 ? <ChartEmpty /> : (
              <>
                <ResponsiveContainer width="50%" height={220}>
                  <PieChart>
                    <Pie
                      data={charts.classification_coverage}
                      dataKey="count"
                      nameKey="category"
                      cx="50%" cy="50%"
                      innerRadius={55} outerRadius={90}
                      paddingAngle={2}
                    >
                      {charts.classification_coverage.map((_, i) => (
                        <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                      ))}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex-1 space-y-1.5 overflow-y-auto max-h-[220px]">
                  {charts.classification_coverage.slice(0, 8).map((d, i) => (
                    <div key={i} className="flex items-center justify-between text-xs gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: PALETTE[i % PALETTE.length] }} />
                        <span className="truncate text-muted-foreground">{d.category}</span>
                      </div>
                      <span className="font-semibold tabular-nums shrink-0">{d.count.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </CardShell>

        {/* Procurement Opportunities */}
        <CardShell>
          <CardHeader icon={<TrendingUp size={15} className="text-primary" />} title="Procurement Opportunities" subtitle="Shared materials across CPSEs — bulk purchasing potential" />
          <div className="p-4">
            {charts.procurement_opportunities.length === 0 ? <ChartEmpty /> : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={charts.procurement_opportunities} layout="vertical" margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} horizontal={false} />
                  <XAxis type="number" tick={{ fill: CHART_THEME.text, fontSize: 10 }} tickFormatter={v => `₹${(v/1000).toFixed(0)}K`} />
                  <YAxis type="category" dataKey="description" tick={{ fill: CHART_THEME.text, fontSize: 10 }} width={100} />
                  <Tooltip content={<ChartTooltip formatter={v => `₹${Number(v).toLocaleString()}`} />} />
                  <Bar dataKey="total_spend" name="Total Spend" fill="#6366f1" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </CardShell>
      </div>

      {/* ── Chart Row 3: Top Redundant + Upload Pipeline Status ───── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Top Redundant Material Groups */}
        <CardShell>
          <CardHeader icon={<Copy size={15} className="text-primary" />} title="Top Redundant Material Groups" subtitle="National codes with the most CPSE duplicates" />
          <div className="p-4">
            {charts.top_redundant.length === 0 ? <ChartEmpty /> : (
              <div className="space-y-2">
                {charts.top_redundant.slice(0, 7).map((d, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground w-4 text-right shrink-0">{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-xs truncate text-foreground">{d.description}</span>
                        <span className="text-xs font-mono text-muted-foreground ml-2 shrink-0">{d.mapped_count}×</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full bg-primary transition-all"
                          style={{ width: `${(d.mapped_count / (charts.top_redundant[0]?.mapped_count || 1)) * 100}%` }}
                        />
                      </div>
                    </div>
                    <span className="text-xs text-muted-foreground shrink-0">{d.cpse_count} CPSEs</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardShell>

        {/* Upload Pipeline Status */}
        <CardShell>
          <CardHeader icon={<Upload size={15} className="text-primary" />} title="Upload Pipeline Status" subtitle="Processing jobs by status" />
          <div className="p-4 flex items-center gap-4">
            {charts.upload_by_status.length === 0 ? <ChartEmpty /> : (
              <>
                <ResponsiveContainer width="50%" height={200}>
                  <PieChart>
                    <Pie data={charts.upload_by_status} dataKey="count" nameKey="status" cx="50%" cy="50%" outerRadius={80} paddingAngle={3}>
                      {charts.upload_by_status.map((d, i) => {
                        const c: Record<string, string> = { COMPLETED: '#10b981', RUNNING: '#6366f1', PENDING: '#f59e0b', FAILED: '#ef4444' };
                        return <Cell key={i} fill={c[d.status] ?? PALETTE[i % PALETTE.length]} />;
                      })}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-2">
                  {charts.upload_by_status.map((d, i) => {
                    const c: Record<string, string> = { COMPLETED: '#10b981', RUNNING: '#6366f1', PENDING: '#f59e0b', FAILED: '#ef4444' };
                    return (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: c[d.status] ?? PALETTE[i] }} />
                        <span className="text-muted-foreground">{d.status}</span>
                        <span className="font-bold ml-auto">{d.count}</span>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </CardShell>
      </div>

      {/* ── Approvals by Type ─────────────────────────────────────── */}
      {charts.approvals_by_type.length > 0 && (
        <CardShell>
          <CardHeader icon={<CheckCircle2 size={15} className="text-primary" />} title="Pending Approvals by Type" subtitle="Breakdown of approval queue by target type and status" />
          <div className="p-4">
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={charts.approvals_by_type} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} />
                <XAxis dataKey="type" tick={{ fill: CHART_THEME.text, fontSize: 11 }} />
                <YAxis tick={{ fill: CHART_THEME.text, fontSize: 11 }} />
                <Tooltip content={<ChartTooltip />} />
                <Legend wrapperStyle={{ fontSize: 11, color: CHART_THEME.text }} />
                <Bar dataKey="count" name="Count" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardShell>
      )}

      {/* ── Activity Feeds ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Recent Uploads */}
        <CardShell>
          <CardHeader icon={<Upload size={14} className="text-primary" />} title="Recent Uploads" />
          <div className="divide-y divide-border">
            {recent.uploads.length === 0 ? (
              <div className="p-4 text-xs text-muted-foreground text-center italic">No uploads yet.</div>
            ) : recent.uploads.map(u => (
              <div key={u.id} className="px-4 py-3 flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{u.filename || 'Unnamed file'}</p>
                  <p className="text-xs text-muted-foreground">{u.timestamp ? new Date(u.timestamp).toLocaleDateString() : '—'}</p>
                </div>
                <StatusPill status={u.status || 'UNKNOWN'} />
              </div>
            ))}
          </div>
        </CardShell>

        {/* Recent Approvals */}
        <CardShell>
          <CardHeader icon={<CheckCircle2 size={14} className="text-primary" />} title="Recent Approvals" />
          <div className="divide-y divide-border">
            {recent.approvals.length === 0 ? (
              <div className="p-4 text-xs text-muted-foreground text-center italic">No approvals yet.</div>
            ) : recent.approvals.map(a => (
              <div key={a.id} className="px-4 py-3 flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-muted-foreground">{a.target_type}</p>
                  <p className="text-sm font-mono text-primary truncate">{a.target_id.slice(0, 16)}…</p>
                  <p className="text-xs text-muted-foreground">{a.approver_id ?? 'System'}</p>
                </div>
                <StatusPill status={a.status} />
              </div>
            ))}
          </div>
        </CardShell>

        {/* Processing Jobs */}
        <CardShell>
          <CardHeader icon={<Activity size={14} className="text-primary" />} title="Processing Jobs" />
          <div className="divide-y divide-border">
            {recent.jobs.length === 0 ? (
              <div className="p-4 text-xs text-muted-foreground text-center italic">No jobs yet.</div>
            ) : recent.jobs.map(j => (
              <div key={j.job_id} className="px-4 py-3 flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-mono text-muted-foreground">{j.job_id.slice(0, 12)}…</p>
                  <p className="text-xs text-muted-foreground">{j.records_processed.toLocaleString()} records</p>
                  <p className="text-xs text-muted-foreground">{j.started_at ? new Date(j.started_at).toLocaleDateString() : '—'}</p>
                </div>
                <StatusPill status={j.status} />
              </div>
            ))}
          </div>
        </CardShell>
      </div>

    </div>
  );
};
