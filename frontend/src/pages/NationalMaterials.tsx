import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Database, RefreshCw, Search, Plus, X, ChevronRight,
  Archive, Edit, Eye, CheckCircle2, Clock,
  AlertTriangle, Hash, Users, FileStack, Layers,
  ImageOff, Star, BookmarkPlus, Pencil
} from 'lucide-react';
import {
  getNationalMaterialsFn, getNationalMaterialDetailFn,
  createNationalMaterialFn, updateNationalMaterialFn, retireNationalMaterialFn,
  type NationalMaterialRead, type NationalMaterialDetail, type NationalMaterialsParams,
  type CpseMappingRow
} from '../api/nationalMaterials';
import { getClassificationsFn, type Classification } from '../api/classifications';
import { getCpsesFn } from '../api/materials';
import { cn } from '../components/common/MetricCard';

// ══════════════════════════════════════════════════════════════
// SHARED PRIMITIVES
// ══════════════════════════════════════════════════════════════

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const cfg: Record<string, string> = {
    ACTIVE:        'bg-green-50 text-green-700 border-green-200',
    PROVISIONAL:   'bg-slate-100 text-slate-600 border-slate-200',
    UNDER_REVIEW:  'bg-amber-50 text-amber-700 border-amber-200',
    REJECTED:      'bg-red-50 text-red-600 border-red-200',
    SUPERSEDED:    'bg-blue-50 text-blue-700 border-blue-200',
    RETIRED:       'bg-red-50 text-red-400 border-red-200 line-through opacity-60',
  };
  return (
    <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border', cfg[status] ?? cfg.PROVISIONAL)}>
      {status}
    </span>
  );
};

const StatChip: React.FC<{ icon: React.ReactNode; label: string; value: number | string }> = ({ icon, label, value }) => (
  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
    <span className="text-primary">{icon}</span>
    <span className="font-semibold text-foreground">{value}</span>
    <span>{label}</span>
  </div>
);

const SectionHeader: React.FC<{ icon: React.ReactNode; title: string }> = ({ icon, title }) => (
  <div className="flex items-center gap-2 px-4 py-2.5 bg-muted/30 border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wider">
    {icon} {title}
  </div>
);

const InfoRow: React.FC<{ label: string; value: React.ReactNode; mono?: boolean }> = ({ label, value, mono }) => (
  <div className="flex items-start gap-3 py-1.5 text-sm border-b border-border/30 last:border-0">
    <span className="text-muted-foreground w-36 shrink-0 text-xs pt-0.5">{label}</span>
    <span className={cn('break-all', mono && 'font-mono text-xs')}>{value ?? '—'}</span>
  </div>
);

// ══════════════════════════════════════════════════════════════
// CREATE / EDIT MODAL
// ══════════════════════════════════════════════════════════════

const nmSchema = z.object({
  primary_description: z.string().min(3, 'Description must be at least 3 characters'),
  category_code:       z.string().optional(),
  uom:                 z.string().optional(),
});

type NMFormData = z.infer<typeof nmSchema>;

const NMModal: React.FC<{
  editData?: NationalMaterialRead | null;
  classifications: Classification[];
  onClose: () => void;
  onSaved: () => void;
}> = ({ editData, classifications, onClose, onSaved }) => {
  const qc = useQueryClient();
  const isEdit = !!editData;

  const { register, handleSubmit, formState: { errors } } = useForm<NMFormData>({
    resolver: zodResolver(nmSchema),
    defaultValues: {
      primary_description: editData?.canonical_description ?? '',
      category_code: editData?.classification_id ?? '',
      uom: editData?.canonical_uom ?? '',
    }
  });

  const createMutation = useMutation({
    mutationFn: createNationalMaterialFn,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['national-materials'] }); onSaved(); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ code, payload }: { code: string; payload: any }) => updateNationalMaterialFn(code, payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['national-materials'] }); onSaved(); },
  });

  const onSubmit = (data: NMFormData) => {
    const payload = {
      canonical_description: data.primary_description,
      classification_id: data.category_code,
      canonical_uom: data.uom,
    };
    if (isEdit) {
      updateMutation.mutate({ code: editData.national_material_id, payload: { ...payload, editor_id: 'DEMO_USER' } });
    } else {
      createMutation.mutate({ ...payload, created_by: 'DEMO_USER' });
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;
  const isError = createMutation.isError || updateMutation.isError;

  return (
    <div className="fixed inset-0 z-60 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-card border border-border rounded-xl shadow-2xl w-full max-w-lg p-6 z-10">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold flex items-center gap-2">
            {isEdit ? <Edit size={18} className="text-primary" /> : <Plus size={18} className="text-primary" />}
            {isEdit ? 'Edit National Material' : 'Create National Material'}
          </h2>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-accent"><X size={16} /></button>
        </div>

        {isError && (
          <div className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center gap-2">
            <AlertTriangle size={14} /> Save failed. Check the code or description.
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Auto-generated code handled by backend now */}
          <div>
            <label className="block text-sm text-muted-foreground mb-1">Canonical Description <span className="text-destructive">*</span></label>
            <textarea {...register('primary_description')} rows={3} className="w-full p-2.5 rounded-md border border-border bg-background text-sm focus:ring-primary focus:outline-none focus:ring-2 focus:ring-offset-0 resize-none" />
            {errors.primary_description && <p className="text-xs text-destructive mt-1">{errors.primary_description.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-muted-foreground mb-1">Classification</label>
              <select {...register('category_code')} className="w-full p-2.5 rounded-md border border-border bg-background text-sm focus:ring-primary focus:outline-none">
                <option value="">— None —</option>
                {classifications.map(c => (
                  <option key={c.code} value={c.code}>{c.name} ({c.code})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-muted-foreground mb-1">UOM</label>
              <input {...register('uom')} placeholder="e.g. EA, KG, LTR" className="w-full p-2.5 rounded-md border border-border bg-background text-sm focus:ring-primary focus:outline-none focus:ring-2" />
            </div>
          </div>
          <div className="flex gap-3 justify-end pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-md border border-border hover:bg-accent text-sm transition-colors">Cancel</button>
            <button
              type="submit"
              disabled={isPending}
              className="px-5 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-60 flex items-center gap-2 transition-colors"
            >
              {isPending && <RefreshCw size={13} className="animate-spin" />}
              {isEdit ? 'Save Changes' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════
// DETAIL DRAWER
// ══════════════════════════════════════════════════════════════

const NMDetailDrawer: React.FC<{
  code: string;
  onClose: () => void;
  onEdit: (nm: NationalMaterialRead) => void;
}> = ({ code, onClose, onEdit }) => {
  const qc = useQueryClient();
  const [retireConfirm, setRetireConfirm] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['national-material-detail', code],
    queryFn: () => getNationalMaterialDetailFn(code),
  });

  const retireMutation = useMutation({
    mutationFn: () => retireNationalMaterialFn(code, 'Retired via UI'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['national-material-detail', code] });
      qc.invalidateQueries({ queryKey: ['national-materials'] });
      setRetireConfirm(false);
    }
  });

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="w-[720px] max-w-[95vw] bg-card border-l border-border flex flex-col overflow-hidden shadow-2xl">

        {/* Header */}
        <div className="px-6 py-4 border-b border-border shrink-0 flex items-center justify-between bg-card/80 backdrop-blur">
          <div className="flex items-center gap-3">
            <Database size={18} className="text-primary" />
            <div>
              <h2 className="font-bold text-lg font-mono">{code}</h2>
              {data && <p className="text-xs text-muted-foreground">{data.canonical_description}</p>}
            </div>
            {data && <StatusBadge status={data.status} />}
          </div>
          <div className="flex items-center gap-2">
            {data && !data.is_retired && (
              <>
                <button onClick={() => onEdit(data)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border hover:bg-accent text-sm transition-colors">
                  <Edit size={13} /> Edit
                </button>
                {!retireConfirm ? (
                  <button onClick={() => setRetireConfirm(true)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-red-500/40 text-red-400 hover:bg-red-500/10 text-sm transition-colors">
                    <Archive size={13} /> Retire
                  </button>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-red-400">Confirm retire?</span>
                    <button onClick={() => retireMutation.mutate()} disabled={retireMutation.isPending} className="px-3 py-1.5 rounded-md bg-red-600 text-white text-xs font-medium hover:bg-red-500 disabled:opacity-60">
                      {retireMutation.isPending ? <RefreshCw size={11} className="animate-spin" /> : 'Yes'}
                    </button>
                    <button onClick={() => setRetireConfirm(false)} className="px-2 py-1.5 rounded-md border border-border text-xs hover:bg-accent">No</button>
                  </div>
                )}
              </>
            )}
            <button onClick={onClose} className="p-1.5 rounded hover:bg-accent"><X size={18} /></button>
          </div>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 p-5 space-y-5">
          {isLoading ? (
            <div className="flex items-center justify-center h-60 text-muted-foreground">
              <RefreshCw size={20} className="animate-spin mr-2" /> Loading…
            </div>
          ) : data ? (
            <>
              {/* ── Product image placeholder + action buttons ── */}
              <div className="flex gap-4 items-start">

                {/* Image placeholder frame */}
                <div
                  className="shrink-0 w-28 h-28 rounded-2xl border-2 border-dashed border-border bg-muted/40 flex flex-col items-center justify-center gap-1.5 cursor-default select-none"
                  title="No product image available"
                >
                  <ImageOff size={22} className="text-muted-foreground/40" />
                  <span className="text-[9px] text-muted-foreground/50 font-medium uppercase tracking-wide">No Image</span>
                </div>

                {/* Right: description + actions */}
                <div className="flex-1 min-w-0">
                  <p className="text-base font-semibold leading-snug mb-1">{data.canonical_description}</p>
                  <div className="flex items-center gap-2 mb-4 flex-wrap">
                    <StatusBadge status={data.status} />
                    {data.canonical_uom && (
                      <span className="text-xs text-muted-foreground font-mono bg-muted px-2 py-0.5 rounded">{data.canonical_uom}</span>
                    )}
                    <span className="text-xs text-muted-foreground">{data.cpse_count} CPSEs · {data.source_count} legacy codes</span>
                  </div>

                  {/* Action buttons */}
                  <div className="flex items-center gap-2 flex-wrap">
                    {/* Primary: Approve & Publish — deep green */}
                    {!data.is_retired && data.status !== 'ACTIVE' && (
                      <button
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold text-white transition-all hover:-translate-y-px"
                        style={{
                          background: 'linear-gradient(135deg, hsl(155,73%,17%), hsl(155,62%,25%))',
                          boxShadow: '0 4px 12px hsl(155 73% 21% / 0.30)',
                        }}
                      >
                        <CheckCircle2 size={14} />
                        Approve &amp; Publish
                      </button>
                    )}
                    {/* Secondary: Suggest Edit — outlined gray-green */}
                    {!data.is_retired && (
                      <button
                        onClick={() => onEdit(data)}
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold border transition-all hover:-translate-y-px"
                        style={{
                          color: 'hsl(155,73%,21%)',
                          borderColor: 'hsl(155 73% 21% / 0.35)',
                          background: 'hsl(155 73% 21% / 0.04)',
                        }}
                      >
                        <Pencil size={13} />
                        Suggest Edit
                      </button>
                    )}
                    {/* Ghost: Add to Watchlist */}
                    <button
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold border border-border bg-white text-muted-foreground hover:bg-muted/60 hover:text-foreground transition-all"
                    >
                      <BookmarkPlus size={13} />
                      Add to Watchlist
                    </button>
                  </div>
                </div>
              </div>

              {/* Identity */}
              <div className="card overflow-hidden">
                <SectionHeader icon={<Hash size={13} />} title="Identity" />
                <div className="p-4">
                  <InfoRow label="National Code" value={data.national_material_code} mono />
                  <InfoRow label="Status" value={<StatusBadge status={data.status} />} />
                  <InfoRow label="UOM" value={data.canonical_uom} mono />
                  <InfoRow label="Created" value={data.created_at ? new Date(data.created_at).toLocaleString() : '—'} />
                  <InfoRow label="Last Updated" value={data.updated_at ? new Date(data.updated_at).toLocaleString() : '—'} />
                </div>
              </div>

              {/* Canonical Description */}
              <div className="card overflow-hidden">
                <SectionHeader icon={<FileStack size={13} />} title="Canonical Description" />
                <div className="p-4">
                  <p className="text-base leading-relaxed">{data.canonical_description}</p>
                </div>
              </div>

              {/* Classification */}
              <div className="card overflow-hidden">
                <SectionHeader icon={<Layers size={13} />} title="Classification" />
                <div className="p-4">
                  {data.classification_breadcrumb.length > 0 ? (
                    <div className="flex items-center flex-wrap gap-1.5 text-sm">
                      {data.classification_breadcrumb.map((c, i) => (
                        <React.Fragment key={c.code}>
                          {i > 0 && <ChevronRight size={13} className="text-muted-foreground" />}
                          <span className="bg-primary/10 text-primary px-2 py-0.5 rounded-full font-medium text-xs">{c.name}</span>
                        </React.Fragment>
                      ))}
                    </div>
                  ) : <p className="text-sm text-muted-foreground italic">No classification assigned.</p>}
                  {data.classification_id && <p className="text-xs text-muted-foreground mt-2">Code: <span className="font-mono">{data.classification_id}</span></p>}
                </div>
              </div>

              {/* Attributes */}
              {data.attributes && Object.keys(data.attributes).length > 0 && (
                <div className="card overflow-hidden">
                  <SectionHeader icon={<Layers size={13} />} title="Canonical Attributes" />
                  <div className="p-4 grid grid-cols-2 gap-2">
                    {Object.entries(data.attributes).map(([k, v]) => (
                      <div key={k} className="bg-muted/40 rounded-lg px-3 py-2">
                        <p className="text-xs text-muted-foreground">{k}</p>
                        <p className="text-sm font-medium">{String(v)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* CPSE Mappings */}
              <div className="card overflow-hidden">
                <SectionHeader icon={<Users size={13} />} title={`CPSE Mappings (${data.source_count} legacy codes, ${data.cpse_count} CPSEs)`} />
                {data.mappings_summary && data.mappings_summary.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/40 border-b border-border">
                        <tr>
                          {['CPSE', 'Legacy Code', 'Description', 'UOM', 'Type', 'Confidence'].map(h => (
                            <th key={h} className="p-3 text-left text-xs font-semibold text-muted-foreground">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {data.mappings_summary.map((m: any) => (
                          <tr key={m.mapping_id} className="border-b border-border/30 hover:bg-primary/3 transition-colors">
                            {/* CPSE chip — green tag */}
                            <td className="p-3">
                              <span
                                className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide"
                                style={{ background: 'hsl(155 73% 21% / 0.10)', color: 'hsl(155,73%,21%)' }}
                              >
                                {m.cpse_code}
                              </span>
                            </td>
                            {/* Legacy code — green chip */}
                            <td className="p-3">
                              <span
                                className="font-mono text-xs px-2 py-0.5 rounded font-semibold"
                                style={{ background: 'hsl(155 73% 21% / 0.08)', color: 'hsl(155,62%,25%)' }}
                              >
                                {m.legacy_material_code}
                              </span>
                            </td>
                            <td className="p-3 text-xs text-muted-foreground max-w-[160px] truncate">{m.description}</td>
                            <td className="p-3 font-mono text-xs">{m.uom ?? '—'}</td>
                            <td className="p-3 text-xs font-semibold">{m.mapping_type}</td>
                            <td className="p-3">
                              {m.confidence !== null ? (
                                <span
                                  className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold tabular-nums border"
                                  style={{
                                    background: m.confidence >= 0.9 ? 'hsl(155 73% 21% / 0.08)' : m.confidence >= 0.7 ? '#fffbeb' : '#fef2f2',
                                    color: m.confidence >= 0.9 ? 'hsl(155,62%,25%)' : m.confidence >= 0.7 ? '#92610a' : '#dc2626',
                                    borderColor: m.confidence >= 0.9 ? 'hsl(155 73% 21% / 0.20)' : m.confidence >= 0.7 ? '#fde68a' : '#fecaca',
                                  }}
                                >
                                  {Math.round(m.confidence * 100)}%
                                </span>
                              ) : '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="p-6 text-sm text-muted-foreground italic text-center">No CPSE mappings yet.</div>
                )}
              </div>

              {/* Audit History */}
              {data.audit_history.length > 0 && (
                <div className="card overflow-hidden">
                  <SectionHeader icon={<Clock size={13} />} title="Audit History" />
                  <div className="p-4 space-y-2">
                    {data.audit_history.map((a, i) => (
                      <div key={i} className="flex items-start gap-3 py-1.5 border-b border-border/30 last:border-0 text-sm">
                        <span className="text-xs text-muted-foreground w-32 shrink-0 pt-0.5">
                          {a.timestamp ? new Date(a.timestamp).toLocaleDateString() : '—'}
                        </span>
                        <div>
                          <span className="font-medium">{a.action}</span>
                          {a.user_id && <span className="text-muted-foreground text-xs ml-2">· {a.user_id}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════
// MAIN PAGE
// ══════════════════════════════════════════════════════════════

export const NationalMaterials: React.FC = () => {
  const [params, setParams] = useState<NationalMaterialsParams>({ limit: 50, offset: 0 });
  const [search, setSearch] = useState('');
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [editTarget, setEditTarget] = useState<NationalMaterialRead | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const setParam = (key: keyof NationalMaterialsParams, value: any) =>
    setParams(p => ({ ...p, [key]: value || undefined, offset: 0 }));

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['national-materials', params],
    queryFn: () => getNationalMaterialsFn(params),
    placeholderData: (prev) => prev,
  });

  const { data: classifications = [] } = useQuery({
    queryKey: ['classifications'],
    queryFn: getClassificationsFn,
  });

  const { data: cpses = [] } = useQuery({
    queryKey: ['cpses'],
    queryFn: getCpsesFn,
  });

  const currentPage = Math.floor((params.offset ?? 0) / (params.limit ?? 50)) + 1;
  const totalPages = data ? Math.ceil(data.total / (params.limit ?? 50)) : 1;

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setParam('search', search);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading flex items-center gap-2">
            <Database size={22} className="text-primary" /> National Material Catalog
          </h1>
          {data && (
            <p className="text-sm text-muted-foreground mt-0.5">
              {data.total.toLocaleString()} golden records — the canonical reference for all CPSEs
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refetch()}
            className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-primary border border-border rounded-lg px-3 py-2 hover:border-primary/40 hover:bg-primary/5 transition-all"
          >
            <RefreshCw size={13} className={cn(isFetching && 'animate-spin text-primary')} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="btn-primary"
          >
            <Plus size={15} /> Create National Material
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4 space-y-3">
        <div className="flex gap-3">
          <form onSubmit={handleSearch} className="flex-1 flex gap-2">
            <div className="relative flex-1">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search by code or canonical description…"
                className="w-full pl-9 pr-4 py-2 rounded-md border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>
            <button type="submit" className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors">Search</button>
          </form>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Classification</label>
            <select className="w-full p-2 rounded-md border border-border bg-background text-sm" onChange={e => setParam('classification_id', e.target.value)}>
              <option value="">All Categories</option>
              {classifications.map((c: Classification) => <option key={c.code} value={c.code}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Status</label>
            <select className="w-full p-2 rounded-md border border-border bg-background text-sm" onChange={e => setParam('status', e.target.value)}>
              <option value="">All Statuses</option>
              <option value="PROVISIONAL">Provisional</option>
              <option value="UNDER_REVIEW">Under Review</option>
              <option value="ACTIVE">Active</option>
              <option value="SUPERSEDED">Superseded</option>
              <option value="REJECTED">Rejected</option>
              <option value="RETIRED">Retired</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">CPSE</label>
            <select className="w-full p-2 rounded-md border border-border bg-background text-sm" onChange={e => setParam('cpse_id', e.target.value)}>
              <option value="">All CPSEs</option>
              {cpses.map((c: any) => <option key={c.cpse_code} value={c.cpse_code}>{c.cpse_name}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 border-b border-border">
              <tr>
                {['National Code', 'Canonical Description', 'Category', 'Classification', 'Status', 'CPSEs', 'Legacy Codes', 'Actions'].map(h => (
                  <th key={h} className="p-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={8} className="p-12 text-center text-muted-foreground"><RefreshCw size={20} className="animate-spin inline mr-2" />Loading…</td></tr>
              ) : data?.items.length === 0 ? (
              <tr><td colSpan={8} className="p-12 text-center text-muted-foreground">
                  <Database size={32} className="mx-auto mb-3 opacity-30" />
                  <p>No national materials found.</p>
                  <p className="text-xs mt-1">Create the first golden record using the button above.</p>
                </td></tr>
              ) : (
                data?.items.map((nm: NationalMaterialRead) => (
                  <tr key={nm.national_material_code} className="border-b border-border/50 hover:bg-primary/3 transition-colors group">
                    <td className="p-3">
                      <button
                        onClick={() => setSelectedCode(nm.national_material_id)}
                        className="font-mono text-xs text-primary hover:underline font-semibold"
                      >
                        {nm.national_material_code}
                      </button>
                    </td>
                    <td className="p-3 max-w-[240px]">
                      <span className="block truncate" title={nm.canonical_description}>{nm.canonical_description}</span>
                    </td>
                    <td className="p-3 text-xs text-muted-foreground font-mono">{nm.classification_id ?? '—'}</td>
                    <td className="p-3 text-xs text-muted-foreground">
                      {nm.classification_breadcrumb?.length > 0 ? nm.classification_breadcrumb[nm.classification_breadcrumb.length - 1].name : '—'}
                    </td>
                    <td className="p-3"><StatusBadge status={nm.status} /></td>
                    <td className="p-3">
                      <StatChip icon={<Users size={11} />} label="CPSEs" value={nm.cpse_count} />
                    </td>
                    <td className="p-3">
                      {/* Legacy codes — green chip count */}
                      <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full"
                        style={{ background: 'hsl(155 73% 21% / 0.09)', color: 'hsl(155,62%,25%)' }}>
                        <FileStack size={10} /> {nm.source_count}
                      </span>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => setSelectedCode(nm.national_material_id)}
                          className="p-1.5 rounded hover:bg-primary/10 text-primary transition-colors"
                          title="View Detail"
                        >
                          <Eye size={14} />
                        </button>
                        {!nm.is_retired && (
                          <button
                            onClick={() => setEditTarget(nm)}
                            className="p-1.5 rounded hover:bg-accent transition-colors"
                            title="Edit"
                          >
                            <Edit size={14} />
                          </button>
                        )}
                      </div>
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
      {selectedCode && (
        <NMDetailDrawer
          code={selectedCode}
          onClose={() => setSelectedCode(null)}
          onEdit={(nm) => { setSelectedCode(null); setEditTarget(nm); }}
        />
      )}

      {/* Create / Edit Modal */}
      {(showCreate || editTarget) && (
        <NMModal
          editData={editTarget}
          classifications={classifications}
          onClose={() => { setShowCreate(false); setEditTarget(null); }}
          onSaved={() => { setShowCreate(false); setEditTarget(null); refetch(); }}
        />
      )}
    </div>
  );
};
