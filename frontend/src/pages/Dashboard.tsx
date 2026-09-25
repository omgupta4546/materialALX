import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, RadialBarChart, RadialBar, AreaChart, Area
} from 'recharts';
import {
  Package, Cpu, Copy, Shuffle, CheckCircle2, ShieldAlert,
  Wrench, TrendingUp, Upload, Clock, RefreshCw, AlertTriangle,
  Database, Star, Zap, Activity,
  ArrowRight, Shield, BarChart2, Layers, Lock, Sun
} from 'lucide-react';
import { getDashboardFn, type DashboardPayload } from '../api/analytics';
import { cn } from '../components/common/MetricCard';
import { useAuthStore } from '../store/authStore';

// ══════════════════════════════════════════════════════════════
// HERO SECTION
// ══════════════════════════════════════════════════════════════

const HeroSection: React.FC<{ kpis: DashboardPayload['kpis'] }> = ({ kpis }) => (
  <div className="-mx-6 -mt-6 mb-6">
    {/* ── Hero Banner ── */}
    <div
      className="relative overflow-hidden"
      style={{
        minHeight: 340,
        backgroundImage: 'url(/hero-bg.jpg)',
        backgroundSize: 'cover',
        backgroundPosition: 'center 40%',
      }}
    >
      {/* Charcoal-green gradient overlay */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'linear-gradient(135deg, rgba(13,27,30,0.93) 0%, rgba(15,59,43,0.88) 45%, rgba(15,91,61,0.75) 100%)',
        }}
      />
      {/* Noise texture overlay for depth */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 200 200\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'n\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23n)\'/%3E%3C/svg%3E")',
          backgroundSize: '200px 200px',
        }}
      />

      {/* Content */}
      <div className="relative z-10 px-8 py-12 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
        {/* Left: Text + CTAs */}
        <div className="max-w-2xl">
          {/* Eyebrow */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold mb-4"
            style={{ background: 'rgba(242,169,59,0.18)', color: '#F2A93B', border: '1px solid rgba(242,169,59,0.3)' }}>
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            National Material Intelligence Platform
          </div>

          {/* Headline */}
          <h1
            className="font-heading font-bold text-white leading-tight mb-3"
            style={{ fontSize: 'clamp(1.8rem, 3.5vw, 2.8rem)', letterSpacing: '-0.02em' }}
          >
            Platform Dashboard
          </h1>

          {/* Subheadline */}
          <p className="text-white/70 text-base leading-relaxed mb-7 max-w-xl">
            Live analytics from backend — all metrics sourced from database.
            AI-driven harmonization across CPSEs, real-time deduplication and governance.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-wrap gap-3">
            <Link
              to="/upload"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white transition-all duration-150 hover:-translate-y-0.5"
              style={{
                background: 'linear-gradient(135deg, #0F5B3D, #1B7A4D)',
                boxShadow: '0 4px 14px rgba(15,91,61,0.5)',
              }}
            >
              <Upload size={16} />
              Upload Materials
              <ArrowRight size={14} />
            </Link>
            <Link
              to="/matches"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition-all duration-150 hover:-translate-y-0.5"
              style={{
                background: 'rgba(255,255,255,0.10)',
                border: '1px solid rgba(255,255,255,0.25)',
                color: '#fff',
                backdropFilter: 'blur(6px)',
              }}
            >
              <Shuffle size={16} />
              Review Matches
            </Link>
          </div>
        </div>

        {/* Right: Floating Trust Badge */}
        <div
          className="shrink-0 rounded-2xl p-4 min-w-[220px]"
          style={{
            background: 'rgba(255,255,255,0.95)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.25)',
            backdropFilter: 'blur(16px)',
          }}
        >
          <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-3">Platform Trust</p>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: 'hsl(155 73% 21% / 0.12)' }}>
                <Shield size={16} className="text-primary" />
              </div>
              <div>
                <p className="text-xs font-semibold text-foreground leading-none">ISO-aligned Governance</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">Role-based access & audit trail</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: 'hsl(36 88% 59% / 0.12)' }}>
                <Zap size={16} style={{ color: '#F2A93B' }} />
              </div>
              <div>
                <p className="text-xs font-semibold text-foreground leading-none">AI-Powered Deduplication</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">Semantic matching across CPSEs</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: 'hsl(207 48% 44% / 0.12)' }}>
                <Lock size={16} style={{ color: '#3B7DA8' }} />
              </div>
              <div>
                <p className="text-xs font-semibold text-foreground leading-none">End-to-End Encrypted</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">Data secured at rest & transit</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    {/* ── Stats Strip ── */}
    <div
      className="bg-white border-b border-border px-8 py-5 grid grid-cols-2 sm:grid-cols-4 gap-6"
      style={{ boxShadow: '0 2px 12px rgba(15,91,61,0.06)' }}
    >
      {[
        { label: 'Source Materials', value: kpis.total_source_materials.toLocaleString(), icon: <Package size={16} /> },
        { label: 'Normalization Rate', value: `${kpis.normalization_pct}%`, icon: <BarChart2 size={16} /> },
        { label: 'Approved Mappings', value: kpis.approved_mappings.toLocaleString(), icon: <CheckCircle2 size={16} /> },
        { label: 'National Codes', value: kpis.total_mapped.toLocaleString(), icon: <Layers size={16} /> },
      ].map((s, i) => (
        <div key={i} className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: 'hsl(155 73% 21% / 0.10)', color: 'hsl(155, 73%, 21%)' }}
          >
            {s.icon}
          </div>
          <div>
            <p
              className="text-xl font-bold leading-none tabular-nums"
              style={{ color: 'hsl(155, 73%, 21%)', fontFamily: 'Poppins, Inter, sans-serif' }}
            >
              {s.value}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5 font-medium">{s.label}</p>
          </div>
        </div>
      ))}
    </div>
  </div>
);

// ══════════════════════════════════════════════════════════════
// CONSTANTS  — green-teal-blue-amber palette for light bg
// ══════════════════════════════════════════════════════════════

// Ordered: green → teal → blue → amber → orange → red
const PALETTE = ['#0F5B3D', '#14b8a6', '#3B7DA8', '#F2A93B', '#f97316', '#ef4444', '#8b5cf6', '#ec4899'];
// Pie/donut uses first 4 accents
const PIE_PALETTE = ['#0F5B3D', '#3B7DA8', '#F2A93B', '#14b8a6', '#f97316', '#ef4444'];

const CHART_THEME = {
  background: 'transparent',
  text: '#64748b',          // slate-500 — visible on white
  grid: 'rgba(0,0,0,0.06)', // subtle dark lines on white
};

// ══════════════════════════════════════════════════════════════
// SHARED COMPONENTS
// ══════════════════════════════════════════════════════════════

// White card shell (replaces glass)
const CardShell: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className }) => (
  <div className={cn('card overflow-hidden', className)}>{children}</div>
);

const CardHeader: React.FC<{ icon: React.ReactNode; title: string; subtitle?: string }> = ({ icon, title, subtitle }) => (
  <div className="px-5 py-4 border-b border-border flex items-start justify-between">
    <div>
      <h3 className="font-semibold text-sm flex items-center gap-2">{icon}{title}</h3>
      {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
    </div>
  </div>
);

// KPI Card — white card with colored icon chip
const KpiCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: number | string;
  sub?: string;
  trend?: 'up' | 'down' | 'neutral';
  color?: string;
  alert?: boolean;
  chipColor?: 'green' | 'blue' | 'amber' | 'teal' | 'red';
}> = ({ icon, label, value, sub, color = 'text-primary', alert, chipColor = 'green' }) => {
  const chipClass = alert ? 'kpi-chip kpi-chip-red' : `kpi-chip kpi-chip-${chipColor}`;
  const valueColor = alert
    ? '#ef4444'
    : chipColor === 'blue'  ? '#3B7DA8'
    : chipColor === 'amber' ? '#92610a'
    : chipColor === 'teal'  ? '#0d6e5b'
    : chipColor === 'red'   ? '#ef4444'
    : 'hsl(155,73%,21%)';
  return (
    <div className="card p-5 flex items-start gap-4">
      <div className={chipClass}>{icon}</div>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1 font-medium">{label}</p>
        <p className="text-2xl font-bold tabular-nums leading-tight" style={{ color: valueColor }}>
          {typeof value === 'number' ? value.toLocaleString() : value}
        </p>
        {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
      </div>
    </div>
  );
};

// Quality Gauge — white card
const QualityGauge: React.FC<{ score: number }> = ({ score }) => {
  const color = score >= 80 ? '#0F5B3D' : score >= 60 ? '#F2A93B' : '#ef4444';
  const label = score >= 80 ? 'Excellent' : score >= 60 ? 'Good' : 'Needs Work';
  const data = [{ name: 'Score', value: score, fill: color }, { name: 'Gap', value: 100 - score, fill: 'transparent' }];
  return (
    <div className="card p-5">
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
    refetchInterval: 30_000,
  });
  const { user } = useAuthStore();

  // Friendly greeting based on time of day
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  const displayName = user?.name || 'there';

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

      {/* ── Welcome greeting ──────────────────────────────────────── */}
      <div className="flex items-center justify-between pt-1">
        <div className="flex items-center gap-3">
          <div className="kpi-chip kpi-chip-amber">
            <Sun size={20} />
          </div>
          <div>
            <h1 className="font-heading font-bold text-foreground text-xl leading-tight">
              {greeting}, {displayName} 👋
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">Here's what's happening on the platform today.</p>
          </div>
        </div>
        <button
          onClick={() => refetch()}
          title="Refresh"
          className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-primary border border-border rounded-lg px-3 py-2 hover:border-primary/40 hover:bg-primary/5 transition-all"
        >
          <RefreshCw size={13} className={cn(isFetching && 'animate-spin text-primary')} />
          Refresh
        </button>
      </div>

      {/* ── Hero + Stats Strip ───────────────────────────────────── */}
      <HeroSection kpis={kpis} />

      {/* ── KPI Row 1: Core Pipeline ─────────────────────────────── */}
      <div>
        <p className="text-xs text-muted-foreground uppercase tracking-widest font-semibold mb-3 pl-1">Pipeline Status</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard icon={<Package size={18} />} label="Source Materials" value={kpis.total_source_materials} sub="Total ingested across all CPSEs" chipColor="green" />
          <KpiCard
            icon={<Cpu size={18} />}
            label="Normalized"
            value={kpis.normalized_materials}
            sub={`${kpis.normalization_pct}% of source catalog`}
            chipColor={kpis.normalization_pct >= 80 ? 'green' : 'amber'}
          />
          <KpiCard icon={<Copy size={18} />} label="Duplicate Candidates" value={kpis.duplicate_candidates} sub="Near-duplicate match results" chipColor="blue" />
          <KpiCard icon={<Shuffle size={18} />} label="Functional Equiv." value={kpis.functional_equivalents} sub="Cross-CPSE functional matches" chipColor="teal" />
        </div>
      </div>

      {/* ── KPI Row 2: Approval & Quality ────────────────────────── */}
      <div>
        <p className="text-xs text-muted-foreground uppercase tracking-widest font-semibold mb-3 pl-1">Approvals & Quality</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard icon={<Clock size={18} />} label="Pending Approvals" value={kpis.pending_approvals} sub="Awaiting human review" chipColor={kpis.pending_approvals > 0 ? 'amber' : 'green'} />
          <KpiCard icon={<CheckCircle2 size={18} />} label="Approved Mappings" value={kpis.approved_mappings} sub={`${kpis.mapping_pct}% of source mapped`} chipColor="green" />
          <KpiCard icon={<ShieldAlert size={18} />} label="High-Risk Matches" value={kpis.high_risk_matches} sub="Critical conflict flag" alert={kpis.high_risk_matches > 0} chipColor="red" />
          <KpiCard icon={<Wrench size={18} />} label="Engineering Reviews" value={kpis.engineering_reviews} sub="Flagged for engineer sign-off" chipColor={kpis.engineering_reviews > 0 ? 'blue' : 'green'} />
        </div>
      </div>

      {/* ── Quality Gauge + Top stats ─────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <QualityGauge score={kpis.data_quality_score} />
        <KpiCard icon={<Database size={18} />} label="Total Matches" value={kpis.total_matches} sub="AI match candidates generated" chipColor="blue" />
        <KpiCard icon={<CheckCircle2 size={18} />} label="Total Mapped" value={kpis.total_mapped} sub="Source → National mappings" chipColor="green" />
        <KpiCard icon={<Zap size={18} />} label="National Codes" value={kpis.approved_mappings} sub="Golden records in catalog" chipColor="teal" />
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
                      <Cell key={i} fill={PIE_PALETTE[i % PIE_PALETTE.length]} />
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
                        <Cell key={i} fill={PIE_PALETTE[i % PIE_PALETTE.length]} />
                      ))}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex-1 space-y-1.5 overflow-y-auto max-h-[220px]">
                  {charts.classification_coverage.slice(0, 8).map((d, i) => (
                    <div key={i} className="flex items-center justify-between text-xs gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: PIE_PALETTE[i % PIE_PALETTE.length] }} />
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
                  <Bar dataKey="total_spend" name="Total Spend" fill="#0F5B3D" radius={[0, 4, 4, 0]} />
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
