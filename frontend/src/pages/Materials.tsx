import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Search, Filter, ChevronUp, ChevronDown, ChevronsUpDown,
  RefreshCw, X, Package, ChevronRight, Cpu, Tag, Info
} from 'lucide-react';
import { getMaterialsFn, getMaterialDetailFn, getCpsesFn, type SourceMaterialSummary, type SourceMaterialDetail, type MaterialsParams } from '../api/materials';
import { cn } from '../components/common/MetricCard';

// ─── Status Badge ──────────────────────────────────────────────
const MappingBadge: React.FC<{ status: string }> = ({ status }) => (
  <span className={cn(
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
    status === 'MAPPED'
      ? "bg-green-500/15 text-green-400 border border-green-500/30"
      : "bg-amber-500/15 text-amber-400 border border-amber-500/30"
  )}>
    {status}
  </span>
);

const ConfidenceBadge: React.FC<{ score: number | null }> = ({ score }) => {
  if (score === null) return <span className="text-muted-foreground text-xs">—</span>;
  const pct = Math.round(score * 100);
  const color = pct >= 90 ? 'text-green-400' : pct >= 70 ? 'text-amber-400' : 'text-red-400';
  return <span className={cn("text-xs font-mono font-semibold", color)}>{pct}%</span>;
};

// ─── Sort Header ───────────────────────────────────────────────
const SortHeader: React.FC<{
  label: string;
  field: string;
  current: string;
  dir: 'asc' | 'desc';
  onSort: (f: string) => void;
}> = ({ label, field, current, dir, onSort }) => (
  <th
    className="p-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider cursor-pointer select-none hover:text-foreground transition-colors whitespace-nowrap"
    onClick={() => onSort(field)}
  >
    <span className="flex items-center gap-1">
      {label}
      {current === field
        ? (dir === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />)
        : <ChevronsUpDown size={12} className="opacity-40" />}
    </span>
  </th>
);

// ─── Detail Drawer ─────────────────────────────────────────────
const DetailDrawer: React.FC<{
  sourceId: string;
  onClose: () => void;
  cpseById: Record<string, string>;
}> = ({ sourceId, onClose, cpseById }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['material-detail', sourceId],
    queryFn: () => getMaterialDetailFn(sourceId),
  });

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Overlay */}
      <div className="flex-1 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div className="w-[640px] bg-card border-l border-border flex flex-col overflow-hidden shadow-2xl">
        <div className="flex items-center justify-between p-5 border-b border-border shrink-0">
          <h2 className="font-bold text-lg flex items-center gap-2">
            <Package size={18} className="text-primary" />
            Material Detail
          </h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-accent transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="overflow-y-auto flex-1 p-5 space-y-6">
          {isLoading ? (
            <div className="flex items-center justify-center h-40 text-muted-foreground">
              <RefreshCw size={20} className="animate-spin mr-2" /> Loading…
            </div>
          ) : data ? (
            <>
              {/* Source Record */}
              <Section title="Source Record" icon={<Tag size={14} />}>
                <Row label="Source ID"       value={data.source_material_id} mono />
                <Row label="Legacy Code"     value={data.legacy_material_code} mono />
                <Row label="Organization"    value={cpseById[data.cpse_id] ?? data.cpse_id} />
                <Row label="Description"     value={data.raw_description} />
                <Row label="UOM"             value={data.raw_uom} />
                <Row label="Category"        value={data.raw_category} />
                <Row label="Manufacturer"    value={data.manufacturer} />
                <Row label="MPN"             value={data.manufacturer_part_number} mono />
                <Row label="Plant"           value={data.plant} />
                <Row label="Source System"   value={data.source_system} />
                <Row label="Source File"     value={data.source_file} />
                <Row label="Specification"   value={data.raw_specification} />
                <Row label="Record Ref"      value={data.source_record_reference} mono />
              </Section>

              {/* Normalized Record */}
              <Section title="Normalized Record" icon={<Cpu size={14} />}>
                {data.normalized_description ? (
                  <>
                    <Row label="Normalized Description" value={data.normalized_description} />
                    <Row label="Category" value={data.raw_category} />
                    <Row label="Manufacturer" value={data.normalized_manufacturer || data.manufacturer} />
                    <Row label="Embedding Ready" value={data.embedding_ready ? '✅ Yes' : '⏳ Pending'} />
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground italic">Not yet normalized.</p>
                )}
              </Section>

              {/* Attributes */}
              {data.attributes && Object.keys(data.attributes).length > 0 && (
                <Section title="Extracted Attributes" icon={<Info size={14} />}>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(data.attributes).map(([k, v]) => (
                      <div key={k} className="bg-muted/40 rounded px-3 py-2">
                        <p className="text-xs text-muted-foreground">{k}</p>
                        <p className="text-sm font-medium">{String(v)}</p>
                      </div>
                    ))}
                  </div>
                </Section>
              )}

              {/* National Mapping */}
              <Section title="National Mapping" icon={<ChevronRight size={14} />}>
                {data.national_material_code ? (
                  <>
                    <Row label="National Code" value={data.national_material_code} mono />
                    <Row label="National Description" value={data.national_description} />
                    <Row label="Mapping Type" value={data.mapping_type} />
                    <Row label="Confidence" value={data.confidence !== null ? `${Math.round(data.confidence * 100)}%` : '—'} />
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground italic">No national mapping yet.</p>
                )}
              </Section>

              {/* Audit History */}
              <Section title="Audit History" icon={<Info size={14} />}>
                {data.audit_history && data.audit_history.length > 0 ? (
                  <div className="space-y-2">
                    {data.audit_history.map((e, i) => (
                      <div key={i} className="flex items-start gap-3 text-sm border-b border-border/50 pb-2">
                        <span className="text-xs text-muted-foreground whitespace-nowrap mt-0.5">
                          {e.timestamp ? new Date(e.timestamp).toLocaleDateString() : '—'}
                        </span>
                        <div>
                          <span className="font-medium text-foreground">{e.action}</span>
                          {e.user_id && <span className="text-muted-foreground"> · {e.user_id}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground italic">No audit events recorded.</p>
                )}
              </Section>
            </>
          ) : (
            <p className="text-muted-foreground">Failed to load material details.</p>
          )}
        </div>
      </div>
    </div>
  );
};

const Section: React.FC<{ title: string; icon: React.ReactNode; children: React.ReactNode }> = ({ title, icon, children }) => (
  <div className="glass rounded-lg overflow-hidden">
    <div className="px-4 py-2.5 bg-muted/30 border-b border-border flex items-center gap-2 text-sm font-semibold text-muted-foreground">
      {icon} {title}
    </div>
    <div className="p-4 space-y-2">{children}</div>
  </div>
);

const Row: React.FC<{ label: string; value: string | null | undefined; mono?: boolean }> = ({ label, value, mono }) => (
  <div className="flex items-start justify-between gap-4 text-sm">
    <span className="text-muted-foreground shrink-0 w-40">{label}</span>
    <span className={cn("text-right break-all", mono && "font-mono text-xs")}>{value ?? '—'}</span>
  </div>
);

// ─── Main Page ─────────────────────────────────────────────────
export const Materials: React.FC = () => {
  const [params, setParams] = useState<MaterialsParams>({
    limit: 50, offset: 0, sort_by: 'created_at', sort_dir: 'desc',
  });
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['materials', params],
    queryFn: () => getMaterialsFn(params),
    placeholderData: (prev) => prev,
  });

  const { data: cpses } = useQuery({
    queryKey: ['cpses'],
    queryFn: getCpsesFn,
  });

  // Build a cpse_id → cpse_name lookup for display purposes
  const cpseById = React.useMemo(() => {
    const map: Record<string, string> = {};
    cpses?.forEach(c => { map[c.cpse_id] = c.cpse_name; });
    return map;
  }, [cpses]);

  const setParam = (key: keyof MaterialsParams, value: any) =>
    setParams(p => ({ ...p, [key]: value || undefined, offset: 0 }));

  const handleSort = (field: string) => {
    setParams(p => ({
      ...p,
      sort_by: field,
      sort_dir: p.sort_by === field && p.sort_dir === 'asc' ? 'desc' : 'asc',
      offset: 0,
    }));
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setParam('q', search);
  };

  const currentPage = Math.floor((params.offset ?? 0) / (params.limit ?? 50)) + 1;
  const totalPages = data ? Math.ceil(data.total / (params.limit ?? 50)) : 1;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Materials Catalog</h1>
          {data && (
            <p className="text-sm text-muted-foreground mt-0.5">
              {data.total.toLocaleString()} records found
            </p>
          )}
        </div>
        <button
          onClick={() => refetch()}
          className="p-2 rounded-md border border-border hover:bg-accent transition-colors"
          title="Refresh"
        >
          <RefreshCw size={16} className={cn(isFetching && 'animate-spin')} />
        </button>
      </div>

      {/* Search & Filter Bar */}
      <div className="glass rounded-xl p-4 space-y-3">
        <div className="flex gap-3">
          <form onSubmit={handleSearch} className="flex-1 flex gap-2">
            <div className="relative flex-1">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={search}
                onChange={e => { setSearch(e.target.value); setParam('q', e.target.value); }}
                placeholder="Search by description, material code…"
                className="w-full pl-9 pr-4 py-2 rounded-md border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-shadow"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
            >
              Search
            </button>
          </form>
          <button
            onClick={() => setFiltersOpen(f => !f)}
            className={cn(
              "px-3 py-2 rounded-md border text-sm flex items-center gap-2 transition-colors",
              filtersOpen ? "bg-primary text-primary-foreground border-primary" : "border-border hover:bg-accent"
            )}
          >
            <Filter size={14} /> Filters
          </button>
        </div>

        {/* Filter Panel */}
        {filtersOpen && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-3 border-t border-border">
            <div>
                <label className="text-xs text-muted-foreground mb-1 block">Organization</label>
              <select
                className="w-full p-2 rounded-md border border-border bg-background text-sm focus:ring-primary"
                onChange={e => setParam('cpse_id', e.target.value || undefined)}
              >
                <option value="">All CPSEs</option>
                {cpses?.map(c => (
                  // send UUID so backend can filter by cpse_id column
                  <option key={c.cpse_id} value={c.cpse_id}>{c.cpse_name} ({c.cpse_code})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Mapping Status</label>
              <select
                className="w-full p-2 rounded-md border border-border bg-background text-sm"
                onChange={e => setParam('mapping_status', e.target.value)}
              >
                <option value="">All</option>
                <option value="MAPPED">Mapped</option>
                <option value="UNMAPPED">Unmapped</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Manufacturer</label>
              <input
                type="text"
                placeholder="Filter by manufacturer…"
                className="w-full p-2 rounded-md border border-border bg-background text-sm"
                onChange={e => setParam('manufacturer', e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">UOM</label>
              <input
                type="text"
                placeholder="e.g. EA, KG, LTR…"
                className="w-full p-2 rounded-md border border-border bg-background text-sm"
                onChange={e => setParam('raw_uom', e.target.value)}
              />
            </div>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="glass rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/30 border-b border-border">
              <tr>
                <SortHeader label="Legacy Code" field="legacy_material_code" current={params.sort_by ?? ''} dir={params.sort_dir ?? 'desc'} onSort={handleSort} />
                <SortHeader label="CPSE" field="cpse_id" current={params.sort_by ?? ''} dir={params.sort_dir ?? 'desc'} onSort={handleSort} />
                <th className="p-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Original Description</th>
                <th className="p-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Normalized</th>
                <SortHeader label="Category" field="raw_category" current={params.sort_by ?? ''} dir={params.sort_dir ?? 'desc'} onSort={handleSort} />
                <th className="p-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Manufacturer</th>
                <SortHeader label="UOM" field="raw_uom" current={params.sort_by ?? ''} dir={params.sort_dir ?? 'desc'} onSort={handleSort} />
                <th className="p-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">National Code</th>
                <th className="p-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
                <th className="p-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={10} className="p-12 text-center text-muted-foreground">
                    <RefreshCw size={20} className="animate-spin inline mr-2" />
                    Loading materials…
                  </td>
                </tr>
              ) : data?.items.length === 0 ? (
                <tr>
                  <td colSpan={10} className="p-12 text-center text-muted-foreground">
                    <Package size={32} className="mx-auto mb-3 opacity-30" />
                    <p>No materials found.</p>
                    <p className="text-xs mt-1">Try adjusting your filters or upload a catalog first.</p>
                  </td>
                </tr>
              ) : (
                data?.items.map((m: SourceMaterialSummary) => (
                  <tr
                    key={m.source_material_id}
                    onClick={() => setSelectedId(m.source_material_id)}
                    className="border-b border-border/50 hover:bg-accent/50 cursor-pointer transition-colors group"
                  >
                    <td className="p-3 font-mono text-xs text-primary">{m.legacy_material_code}</td>
                    <td className="p-3">
                      <span className="text-xs bg-secondary px-2 py-0.5 rounded font-medium" title={m.cpse_id}>
                        {cpseById[m.cpse_id] ?? m.cpse_id}
                      </span>
                    </td>
                    <td className="p-3 max-w-[200px]">
                      <span className="block truncate" title={m.raw_description ?? undefined}>{m.raw_description}</span>
                    </td>
                    <td className="p-3 max-w-[200px] text-muted-foreground">
                      <span className="block truncate" title={m.normalized_description ?? ''}>{m.normalized_description ?? <i>—</i>}</span>
                    </td>
                    <td className="p-3 text-xs text-muted-foreground">{m.raw_category ?? '—'}</td>
                    <td className="p-3 text-xs text-muted-foreground">{m.manufacturer ?? '—'}</td>
                    <td className="p-3 text-xs font-mono">{m.raw_uom ?? '—'}</td>
                    <td className="p-3 font-mono text-xs text-primary">{m.national_material_code ?? '—'}</td>
                    <td className="p-3"><MappingBadge status={m.mapping_status} /></td>
                    <td className="p-3"><ConfidenceBadge score={m.confidence} /></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && data.total > 0 && (
          <div className="px-4 py-3 border-t border-border flex items-center justify-between text-sm text-muted-foreground">
            <span>
              Showing {(params.offset ?? 0) + 1}–{Math.min((params.offset ?? 0) + (params.limit ?? 50), data.total)} of {data.total.toLocaleString()}
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={currentPage <= 1}
                onClick={() => setParams(p => ({ ...p, offset: Math.max(0, (p.offset ?? 0) - (p.limit ?? 50)) }))}
                className="px-3 py-1.5 rounded border border-border hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <span className="px-3 py-1.5 rounded border border-border bg-primary/10 text-primary font-medium">
                {currentPage} / {totalPages}
              </span>
              <button
                disabled={!data.has_more}
                onClick={() => setParams(p => ({ ...p, offset: (p.offset ?? 0) + (p.limit ?? 50) }))}
                className="px-3 py-1.5 rounded border border-border hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Detail Drawer */}
      {selectedId && <DetailDrawer sourceId={selectedId} onClose={() => setSelectedId(null)} cpseById={cpseById} />}
    </div>
  );
};
