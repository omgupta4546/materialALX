import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, RadialBarChart, RadialBar, Legend
} from 'recharts';
import {
  TrendingUp, Activity, ShieldAlert, Database, Cpu,
  CheckCircle2, AlertTriangle, BarChart3, RefreshCw
} from 'lucide-react';
import {
  getDataQualityFn, getProcessingHealthFn, getRiskDistributionFn,
  getConfidenceDistributionFn, getClassificationCoverageFn,
  getMaterialsByCpseFn, getOverviewFn
} from '../api/analytics';
import { cn } from '../components/common/MetricCard';

const PALETTE = ['#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#14b8a6'];
const RISK_COLORS: Record<string, string> = { 'Low Risk': '#10b981', 'Medium Risk': '#f59e0b', 'High Risk': '#ef4444' };
const CHART_THEME = { text: '#94a3b8', grid: 'rgba(148,163,184,0.08)' };

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

const ChartTooltip: React.FC<{ active?: boolean; payload?: any[]; label?: any }> = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass border border-border rounded-lg px-3 py-2 text-xs shadow-xl">
      {label && <p className="font-semibold mb-1">{label}</p>}
      {payload.map((p: any, i: number) => (
        <p key={i} style={{ color: p.color || p.fill }}>{p.name}: <span className="font-bold">{p.value?.toLocaleString()}</span></p>
      ))}
    </div>
  );
};

// ── Quality Gauge ──────────────────────────────────────────────
const GaugeCard: React.FC<{ label: string; score: number; icon: React.ReactNode }> = ({ label, score, icon }) => {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? '#10b981' : pct >= 60 ? '#f59e0b' : '#ef4444';
  const data = [{ value: pct, fill: color }, { value: 100 - pct, fill: 'transparent' }];
  return (
    <CardShell>
      <div className="p-5">
        <div className="flex items-center gap-2 mb-2">
          {icon}
          <span className="text-xs text-muted-foreground uppercase tracking-wider">{label}</span>
        </div>
        <div className="flex items-center justify-center">
          <div className="relative">
            <RadialBarChart width={120} height={120} cx={60} cy={60} innerRadius={38} outerRadius={55} data={data} startAngle={180} endAngle={0}>
              <RadialBar dataKey="value" cornerRadius={8} background={false} />
            </RadialBarChart>
            <div className="absolute inset-0 flex flex-col items-center justify-center" style={{ top: 14 }}>
              <p className="text-2xl font-bold" style={{ color }}>{pct}%</p>
            </div>
          </div>
        </div>
      </div>
    </CardShell>
  );
};

// ── Stat Card ──────────────────────────────────────────────
const StatCard: React.FC<{ icon: React.ReactNode; label: string; value: string | number; sub?: string; color?: string }> = ({ icon, label, value, sub, color = 'text-primary' }) => (
  <CardShell>
    <div className="p-5">
      <div className="inline-flex p-2.5 rounded-lg mb-3 bg-primary/10 text-primary">{icon}</div>
      <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{label}</p>
      <p className={cn('text-2xl font-bold tabular-nums', color)}>{typeof value === 'number' ? value.toLocaleString() : value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  </CardShell>
);

export const Analytics: React.FC = () => {
  const { data: dq, isLoading: dqLoading } = useQuery({ queryKey: ['analytics-dq'], queryFn: () => getDataQualityFn() });
  const { data: health } = useQuery({ queryKey: ['analytics-health'], queryFn: () => getProcessingHealthFn() });
  const { data: risk } = useQuery({ queryKey: ['analytics-risk'], queryFn: () => getRiskDistributionFn() });
  const { data: confidence } = useQuery({ queryKey: ['analytics-confidence'], queryFn: () => getConfidenceDistributionFn() });
  const { data: coverage } = useQuery({ queryKey: ['analytics-coverage'], queryFn: () => getClassificationCoverageFn() });
  const { data: byCpse } = useQuery({ queryKey: ['analytics-cpse'], queryFn: () => getMaterialsByCpseFn() });
  const { data: overview } = useQuery({ queryKey: ['analytics-overview'], queryFn: () => getOverviewFn() });

  if (dqLoading) {
    return (
      <div className="flex items-center justify-center h-96 text-muted-foreground">
        <RefreshCw size={24} className="animate-spin mr-3" /><span>Loading analytics...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-10">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Advanced Analytics</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Data quality, processing health, risk analysis, and classification metrics</p>
      </div>

      {/* ── Data Quality Gauges ───────────────────────────────────── */}
      <div>
        <p className="text-xs text-muted-foreground uppercase tracking-widest font-semibold mb-3 pl-1">Data Quality Scores</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <GaugeCard label="Completeness" score={dq?.avg_completeness ?? 0} icon={<Database size={14} className="text-primary" />} />
          <GaugeCard label="Uniqueness" score={dq?.avg_uniqueness ?? 0} icon={<Cpu size={14} className="text-cyan-400" />} />
          <GaugeCard label="Validity" score={dq?.avg_validity ?? 0} icon={<CheckCircle2 size={14} className="text-green-400" />} />
          <GaugeCard label="Consistency" score={dq?.avg_consistency ?? 0} icon={<Activity size={14} className="text-purple-400" />} />
        </div>
      </div>

      {/* ── Processing Pipeline Stats ──────────────────────────── */}
      <div>
        <p className="text-xs text-muted-foreground uppercase tracking-widest font-semibold mb-3 pl-1">Processing Pipeline</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon={<BarChart3 size={18} />} label="Total Jobs" value={health?.total_jobs ?? 0} sub="Processing runs completed" />
          <StatCard icon={<Database size={18} />} label="Records Processed" value={health?.total_records_processed ?? 0} sub="Total records through pipeline" />
          <StatCard icon={<TrendingUp size={18} />} label="Match Rate" value={overview ? `${overview.mapping_pct}%` : '0%'} sub="Source materials mapped" color={overview && overview.mapping_pct >= 80 ? 'text-green-400' : 'text-amber-400'} />
          <StatCard icon={<AlertTriangle size={18} />} label="High Risk" value={overview?.high_risk_matches ?? 0} sub="Matches needing attention" color={(overview?.high_risk_matches ?? 0) > 0 ? 'text-red-400' : 'text-green-400'} />
        </div>
      </div>

      {/* ── Charts Row 1: Risk + Confidence ──────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Risk Distribution */}
        <CardShell>
          <CardHeader icon={<ShieldAlert size={15} className="text-red-400" />} title="Risk Distribution" subtitle="Match risk level breakdown" />
          <div className="p-4 flex items-center gap-4">
            {risk && risk.length > 0 ? (
              <>
                <ResponsiveContainer width="55%" height={220}>
                  <PieChart>
                    <Pie data={risk} dataKey="count" nameKey="risk_level" cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={3}>
                      {risk.map((d, i) => <Cell key={i} fill={RISK_COLORS[d.risk_level] ?? PALETTE[i % PALETTE.length]} />)}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-3">
                  {risk.map((d, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: RISK_COLORS[d.risk_level] ?? PALETTE[i] }} />
                      <span className="text-muted-foreground">{d.risk_level}</span>
                      <span className="font-bold ml-auto">{d.count}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center w-full h-[220px] text-muted-foreground text-xs"><Activity size={20} className="mr-2 opacity-30" />No risk data</div>
            )}
          </div>
        </CardShell>

        {/* Confidence Distribution */}
        <CardShell>
          <CardHeader icon={<TrendingUp size={15} className="text-primary" />} title="Confidence Distribution" subtitle="Mapping confidence score bands" />
          <div className="p-4">
            {confidence && confidence.some(d => d.count > 0) ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={confidence} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} />
                  <XAxis dataKey="range" tick={{ fill: CHART_THEME.text, fontSize: 11 }} />
                  <YAxis tick={{ fill: CHART_THEME.text, fontSize: 11 }} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="count" name="Mappings" radius={[4, 4, 0, 0]}>
                    {confidence.map((_, i) => <Cell key={i} fill={['#10b981', '#06b6d4', '#f59e0b', '#ef4444'][i % 4]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[220px] text-muted-foreground text-xs">No confidence data</div>
            )}
          </div>
        </CardShell>
      </div>

      {/* ── Charts Row 2: Classification + CPSE ─────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Classification Coverage */}
        <CardShell>
          <CardHeader icon={<BarChart3 size={15} className="text-primary" />} title="Classification Coverage" subtitle="Materials by taxonomy category" />
          <div className="p-4">
            {coverage && coverage.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={coverage} layout="vertical" margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} horizontal={false} />
                  <XAxis type="number" tick={{ fill: CHART_THEME.text, fontSize: 10 }} />
                  <YAxis type="category" dataKey="category" tick={{ fill: CHART_THEME.text, fontSize: 10 }} width={80} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="count" name="Materials" radius={[0, 4, 4, 0]}>
                    {coverage.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[260px] text-muted-foreground text-xs">No classification data</div>
            )}
          </div>
        </CardShell>

        {/* Materials by CPSE */}
        <CardShell>
          <CardHeader icon={<Database size={15} className="text-primary" />} title="Materials by Organization" subtitle="Source material distribution across CPSEs" />
          <div className="p-4">
            {byCpse && byCpse.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={byCpse} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} />
                  <XAxis dataKey="cpse" tick={{ fill: CHART_THEME.text, fontSize: 11 }} />
                  <YAxis tick={{ fill: CHART_THEME.text, fontSize: 11 }} />
                  <Tooltip content={<ChartTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 11, color: CHART_THEME.text }} />
                  <Bar dataKey="count" name="Source Materials" radius={[4, 4, 0, 0]}>
                    {byCpse.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[260px] text-muted-foreground text-xs">No CPSE data</div>
            )}
          </div>
        </CardShell>
      </div>

      {/* ── Pipeline Overview Table ──────────────────────────────── */}
      {overview && (
        <CardShell>
          <CardHeader icon={<Activity size={15} className="text-primary" />} title="Pipeline Overview" subtitle="End-to-end material harmonization metrics" />
          <div className="p-5">
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
              {[
                { label: 'Source Materials', value: overview.total_source_materials },
                { label: 'Normalized', value: overview.normalized_materials },
                { label: 'Matches Found', value: overview.total_matches },
                { label: 'Duplicates', value: overview.duplicate_candidates },
                { label: 'Func. Equiv.', value: overview.functional_equivalents },
                { label: 'Approved', value: overview.approved_mappings },
                { label: 'Pending', value: overview.pending_approvals },
              ].map((item, i) => (
                <div key={i} className="text-center p-3 rounded-lg bg-muted/30">
                  <p className="text-2xl font-bold tabular-nums">{item.value.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-1">{item.label}</p>
                </div>
              ))}
            </div>
            {/* Progress bar */}
            <div className="mt-4">
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span>Normalization Progress</span>
                <span>{overview.normalization_pct}%</span>
              </div>
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${overview.normalization_pct}%` }} />
              </div>
              <div className="flex justify-between text-xs text-muted-foreground mb-1 mt-3">
                <span>Mapping Progress</span>
                <span>{overview.mapping_pct}%</span>
              </div>
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div className="h-full rounded-full bg-green-500 transition-all" style={{ width: `${overview.mapping_pct}%` }} />
              </div>
            </div>
          </div>
        </CardShell>
      )}
    </div>
  );
};
