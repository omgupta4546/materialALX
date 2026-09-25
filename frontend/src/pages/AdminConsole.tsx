import React, { useState, useEffect, useCallback, ReactNode } from 'react';
import axios from 'axios';
import { useAuthStore } from '../store/authStore';
import {
  Users, Shield, Building2, FolderTree, Scale, BookOpen,
  Cpu, FileText, BarChart3, ScrollText, GitMerge, AlertCircle,
  Plus, Pencil, Trash2, RefreshCw, CheckCircle, XCircle,
  ChevronDown, ChevronUp, Search, Lock, Eye, Download, PackageOpen
} from 'lucide-react';

import { DataExportsSection } from '../components/DataExportsSection';
import { MigrationSection } from '../components/MigrationSection';

const API = 'http://localhost:8000/api/v1';

// ──────────────────────────────────────────────────────────────────────────────
// Shared helpers
// ──────────────────────────────────────────────────────────────────────────────

function Badge({ text, color }: { text: string; color: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${color}`}>
      {text}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    ACTIVE: 'bg-green-900/50 text-green-400 border-green-700',
    INACTIVE: 'bg-gray-800 text-gray-500 border-gray-700',
    DEPRECATED: 'bg-orange-900/50 text-orange-400 border-orange-700',
    ARCHIVED: 'bg-gray-800 text-gray-500 border-gray-700',
    SUSPENDED: 'bg-red-900/50 text-red-400 border-red-700',
    PENDING: 'bg-yellow-900/50 text-yellow-400 border-yellow-700',
  };
  return <Badge text={status} color={map[status] ?? 'bg-gray-800 text-gray-400 border-gray-700'} />;
}

function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-gray-900 border border-gray-800 rounded-xl shadow-xl ${className}`}>
      {children}
    </div>
  );
}

function SectionTitle({ icon, title, subtitle }: { icon: ReactNode; title: string; subtitle: string }) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <div className="p-2 bg-primary-900/40 rounded-lg border border-primary-800">{icon}</div>
      <div>
        <h3 className="font-bold text-gray-100 text-lg">{title}</h3>
        <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>
      </div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return <p className="text-gray-600 text-sm py-8 text-center">{message}</p>;
}

function AdminOnly({ children, isAdmin }: { children: ReactNode; isAdmin: boolean }) {
  if (!isAdmin) return (
    <div className="flex items-center gap-2 text-yellow-500 text-xs bg-yellow-900/20 border border-yellow-800 rounded-lg px-3 py-2 mb-4">
      <Lock className="w-3.5 h-3.5" /> Read-only — Admin role required to make changes
    </div>
  );
  return <>{children}</>;
}

// Debounced input
function SearchBar({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <div className="relative mb-4">
      <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-600" />
      <input
        value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-gray-950 border border-gray-800 rounded-lg pl-9 pr-4 py-2 text-sm focus:ring-2 focus:ring-primary-600"
      />
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Generic Table
// ──────────────────────────────────────────────────────────────────────────────

function Table<T extends Record<string, any>>({
  columns, rows, actions
}: {
  columns: { key: string; label: string; render?: (v: any, row: T) => ReactNode }[];
  rows: T[];
  actions?: (row: T) => ReactNode;
}) {
  if (!rows.length) return <EmptyState message="No records found." />;
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-800/50 text-gray-400 text-xs">
            {columns.map(c => (
              <th key={c.key} className="px-4 py-3 text-left font-medium">{c.label}</th>
            ))}
            {actions && <th className="px-4 py-3 text-left font-medium">Actions</th>}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-gray-800/30 transition-colors">
              {columns.map(c => (
                <td key={c.key} className="px-4 py-3 text-gray-300">
                  {c.render ? c.render(row[c.key], row) : String(row[c.key] ?? '—')}
                </td>
              ))}
              {actions && <td className="px-4 py-3">{actions(row)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Modal
// ──────────────────────────────────────────────────────────────────────────────

function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-lg shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <h4 className="font-semibold text-gray-100">{title}</h4>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 transition-colors">✕</button>
        </div>
        <div className="px-6 py-5 space-y-4">{children}</div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <label className="text-xs text-gray-500 mb-1 block font-medium">{label}</label>
      {children}
    </div>
  );
}

function Input({ value, onChange, placeholder, disabled = false }: {
  value: string; onChange: (v: string) => void; placeholder?: string; disabled?: boolean;
}) {
  return (
    <input
      value={value} onChange={e => onChange(e.target.value)}
      placeholder={placeholder} disabled={disabled}
      className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-600 disabled:opacity-40"
    />
  );
}

function SaveBtn({ onClick, label = 'Save', disabled = false }: { onClick: () => void; label?: string; disabled?: boolean }) {
  return (
    <button
      onClick={onClick} disabled={disabled}
      className="w-full py-2.5 rounded-lg bg-gradient-to-r from-primary-700 to-primary-600 hover:from-primary-600 hover:to-primary-500 text-white font-medium text-sm transition-all disabled:opacity-40"
    >
      {label}
    </button>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Section: USERS
// ──────────────────────────────────────────────────────────────────────────────

function UsersSection({ headers, isAdmin }: { headers: any; isAdmin: boolean }) {
  const [users, setUsers] = useState<any[]>([]);
  const [filter, setFilter] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ user_id: '', name: '', email: '', role_id: 'ENGINEER', cpse_code: '' });
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    try { const r = await axios.get(`${API}/admin/users`, { headers }); setUsers(r.data); } catch {}
  }, []);
  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    setErr('');
    try {
      await axios.post(`${API}/admin/users`, form, { headers });
      setModalOpen(false); load();
    } catch (e: any) { setErr(e.response?.data?.detail || 'Error'); }
  };

  const deactivate = async (uid: string) => {
    if (!window.confirm('Deactivate this user?')) return;
    await axios.delete(`${API}/admin/users/${uid}`, { headers }); load();
  };

  const filtered = users.filter(u =>
    `${u.name} ${u.email} ${u.role_id}`.toLowerCase().includes(filter.toLowerCase())
  );

  const ROLE_COLORS: Record<string, string> = {
    ADMIN: 'bg-purple-900/50 text-purple-300 border-purple-700',
    ENGINEER: 'bg-blue-900/50 text-blue-300 border-blue-700',
    DATA_STEWARD: 'bg-teal-900/50 text-teal-300 border-teal-700',
    VIEWER: 'bg-gray-800 text-gray-400 border-gray-700',
  };

  return (
    <div>
      <SectionTitle icon={<Users className="w-5 h-5 text-primary-400" />} title="Users" subtitle={`${users.length} user accounts`} />
      <div className="flex gap-3 mb-4">
        <div className="flex-1"><SearchBar value={filter} onChange={setFilter} placeholder="Filter by name, email, role…" /></div>
        {isAdmin && (
          <button onClick={() => setModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-700 hover:bg-primary-600 text-white rounded-lg text-sm transition-colors shrink-0">
            <Plus className="w-4 h-4" /> Add User
          </button>
        )}
      </div>

      <Table
        columns={[
          { key: 'user_id', label: 'ID', render: (v) => <code className="text-xs text-gray-500">{v}</code> },
          { key: 'name', label: 'Name' },
          { key: 'email', label: 'Email', render: (v) => <span className="text-gray-400">{v || '—'}</span> },
          { key: 'role_id', label: 'Role', render: (v) => <Badge text={v || '?'} color={ROLE_COLORS[v] ?? 'bg-gray-800 text-gray-400 border-gray-700'} /> },
          { key: 'cpse_code', label: 'CPSE', render: (v) => <span className="text-gray-400">{v || 'Global'}</span> },
          { key: 'is_retired', label: 'Status', render: (v) => <StatusBadge status={v ? 'INACTIVE' : 'ACTIVE'} /> },
        ]}
        rows={filtered}
        actions={isAdmin ? (row) => (
          <button onClick={() => deactivate(row.user_id)} disabled={row.is_retired}
            className="p-1 hover:text-red-400 text-gray-600 transition-colors disabled:opacity-30">
            <Trash2 className="w-4 h-4" />
          </button>
        ) : undefined}
      />

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Add User">
        <Field label="User ID"><Input value={form.user_id} onChange={v => setForm(f => ({ ...f, user_id: v }))} placeholder="usr_jane" /></Field>
        <Field label="Name"><Input value={form.name} onChange={v => setForm(f => ({ ...f, name: v }))} /></Field>
        <Field label="Email"><Input value={form.email} onChange={v => setForm(f => ({ ...f, email: v }))} /></Field>
        <Field label="Role">
          <select value={form.role_id} onChange={e => setForm(f => ({ ...f, role_id: e.target.value }))}
            className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm">
            {['ADMIN', 'ENGINEER', 'DATA_STEWARD', 'VIEWER'].map(r => <option key={r}>{r}</option>)}
          </select>
        </Field>
        <Field label="CPSE Code (leave blank for global)"><Input value={form.cpse_code} onChange={v => setForm(f => ({ ...f, cpse_code: v }))} placeholder="NTPC" /></Field>
        {err && <p className="text-red-400 text-xs">{err}</p>}
        <SaveBtn onClick={submit} label="Create User" />
      </Modal>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Section: ROLES
// ──────────────────────────────────────────────────────────────────────────────

function RolesSection({ headers, isAdmin }: { headers: any; isAdmin: boolean }) {
  const [roles, setRoles] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ id: '', description: '' });
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    try { const r = await axios.get(`${API}/admin/roles`, { headers }); setRoles(r.data); } catch {}
  }, []);
  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    setErr('');
    try {
      await axios.post(`${API}/admin/roles`, form, { headers });
      setModalOpen(false); load();
    } catch (e: any) { setErr(e.response?.data?.detail || 'Error'); }
  };

  return (
    <div>
      <SectionTitle icon={<Shield className="w-5 h-5 text-violet-400" />} title="Roles" subtitle="System role definitions" />
      <div className="flex justify-end mb-4">
        {isAdmin && (
          <button onClick={() => setModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-violet-700 hover:bg-violet-600 text-white rounded-lg text-sm">
            <Plus className="w-4 h-4" /> New Role
          </button>
        )}
      </div>
      <Table
        columns={[
          { key: 'id', label: 'Role ID', render: (v) => <code className="text-primary-300 bg-primary-950/50 px-2 py-0.5 rounded text-xs">{v}</code> },
          { key: 'description', label: 'Description', render: (v) => <span className="text-gray-400">{v || '—'}</span> },
        ]}
        rows={roles}
      />
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New Role">
        <Field label="Role ID"><Input value={form.id} onChange={v => setForm(f => ({ ...f, id: v }))} placeholder="ANALYST" /></Field>
        <Field label="Description"><Input value={form.description} onChange={v => setForm(f => ({ ...f, description: v }))} /></Field>
        {err && <p className="text-red-400 text-xs">{err}</p>}
        <SaveBtn onClick={submit} label="Create Role" />
      </Modal>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Section: CPSEs
// ──────────────────────────────────────────────────────────────────────────────

function CPSESection({ headers, isAdmin }: { headers: any; isAdmin: boolean }) {
  const [cpses, setCpses] = useState<any[]>([]);
  const [filter, setFilter] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ cpse_code: '', cpse_name: '', sector: '' });
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    try { const r = await axios.get(`${API}/admin/cpses`, { headers }); setCpses(r.data); } catch {}
  }, []);
  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    setErr('');
    try {
      await axios.post(`${API}/admin/cpses`, form, { headers });
      setModalOpen(false); load();
    } catch (e: any) { setErr(e.response?.data?.detail || 'Error'); }
  };

  const filtered = cpses.filter(c => `${c.cpse_code} ${c.cpse_name} ${c.sector}`.toLowerCase().includes(filter.toLowerCase()));

  // Add consistent color generator for CPSE badges
  const getColor = (code: string) => {
    const colors = ['bg-blue-100 text-blue-700', 'bg-teal-100 text-teal-700', 'bg-amber-100 text-amber-700', 'bg-green-100 text-green-700', 'bg-purple-100 text-purple-700'];
    let hash = 0;
    for (let i = 0; i < code.length; i++) hash = code.charCodeAt(i) + ((hash << 5) - hash);
    return colors[Math.abs(hash) % colors.length];
  };

  return (
    <div>
      <SectionTitle icon={<Building2 className="w-5 h-5 text-blue-400" />} title="Organizations" subtitle={`${cpses.length} registered partner enterprises`} />
      <div className="flex gap-3 mb-6">
        <div className="flex-1"><SearchBar value={filter} onChange={setFilter} placeholder="Filter by code, name, sector…" /></div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5 mb-8">
        {filtered.map(c => (
          <div key={c.cpse_code} className="bg-white rounded-xl p-5 flex flex-col items-center text-center shadow-[0_2px_8px_rgba(0,0,0,0.06)] border border-gray-100 hover:shadow-[0_4px_16px_rgba(0,0,0,0.08)] transition-all group">
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center text-2xl font-bold mb-4 shadow-sm group-hover:scale-105 transition-transform ${getColor(c.cpse_code)}`}>
              {c.cpse_code.substring(0, 2).toUpperCase()}
            </div>
            <h4 className="font-semibold text-gray-900 text-sm mb-1 leading-snug">{c.cpse_name}</h4>
            <div className="flex flex-wrap items-center justify-center gap-2 text-[11px] mt-auto pt-3">
              <span className="text-gray-600 bg-gray-100 border border-gray-200 px-2 py-0.5 rounded-md font-medium">{c.cpse_code}</span>
              {c.sector && <span className="text-gray-600 bg-gray-100 border border-gray-200 px-2 py-0.5 rounded-md font-medium">{c.sector}</span>}
              {c.status && <span className={c.status === 'ACTIVE' ? 'text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded-md font-medium' : 'text-gray-600 bg-gray-100 border border-gray-200 px-2 py-0.5 rounded-md font-medium'}>{c.status}</span>}
            </div>
          </div>
        ))}

        {/* More CPSEs Add Button Tile */}
        {isAdmin && (
          <button onClick={() => setModalOpen(true)} className="bg-gray-50/50 rounded-xl p-5 flex flex-col items-center justify-center text-center border-2 border-dashed border-gray-300 hover:border-[#0F5B3D] hover:bg-[#F5F8F6] transition-all group min-h-[200px]">
            <div className="w-12 h-12 rounded-full flex items-center justify-center bg-gray-200 group-hover:bg-[#0F5B3D]/10 text-gray-500 group-hover:text-[#0F5B3D] mb-3 transition-colors">
              <Plus className="w-6 h-6" />
            </div>
            <span className="font-semibold text-gray-800 group-hover:text-[#0F5B3D] text-sm">More CPSEs</span>
            <span className="text-[11px] text-gray-500 mt-1">Register new organization</span>
          </button>
        )}
      </div>

      {/* Footer Banner */}
      <div className="rounded-xl overflow-hidden bg-white shadow-[0_2px_8px_rgba(0,0,0,0.06)] border border-gray-100 relative">
        <div className="absolute top-0 left-0 right-0 h-1.5" style={{ background: 'linear-gradient(to right, #0F5B3D 0%, #FFFFFF 50%, #F2A93B 100%)' }} />
        <div className="p-5 pt-6 flex items-center justify-center gap-3">
          <Building2 className="w-4 h-4 text-[#0F5B3D]" />
          <span className="text-sm font-semibold text-gray-800 tracking-wide">Empowering National Enterprise Collaboration</span>
        </div>
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Add CPSE">
        <Field label="CPSE Code"><Input value={form.cpse_code} onChange={v => setForm(f => ({ ...f, cpse_code: v }))} placeholder="NTPC" /></Field>
        <Field label="Name"><Input value={form.cpse_name} onChange={v => setForm(f => ({ ...f, cpse_name: v }))} /></Field>
        <Field label="Sector"><Input value={form.sector} onChange={v => setForm(f => ({ ...f, sector: v }))} placeholder="Power" /></Field>
        {err && <p className="text-red-400 text-xs">{err}</p>}
        <SaveBtn onClick={submit} label="Register CPSE" />
      </Modal>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Section: UOM Master
// ──────────────────────────────────────────────────────────────────────────────

function UOMSection({ headers, isAdmin }: { headers: any; isAdmin: boolean }) {
  const [uoms, setUoms] = useState<any[]>([]);
  const [filter, setFilter] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ canonical_code: '', name: '', dimension: '', aliases: '', base_multiplier: '1.0' });
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    try { const r = await axios.get(`${API}/admin/uoms`, { headers }); setUoms(r.data); } catch {}
  }, []);
  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    setErr('');
    try {
      await axios.post(`${API}/admin/uoms`, {
        ...form, aliases: form.aliases.split(',').map(s => s.trim()).filter(Boolean),
        base_multiplier: parseFloat(form.base_multiplier),
      }, { headers });
      setModalOpen(false); load();
    } catch (e: any) { setErr(e.response?.data?.detail || 'Error'); }
  };

  const filtered = uoms.filter(u => `${u.canonical_code} ${u.name} ${u.dimension}`.toLowerCase().includes(filter.toLowerCase()));

  return (
    <div>
      <SectionTitle icon={<Scale className="w-5 h-5 text-teal-400" />} title="UOM Master" subtitle={`${uoms.length} units of measure`} />
      <div className="flex gap-3 mb-4">
        <div className="flex-1"><SearchBar value={filter} onChange={setFilter} placeholder="Filter by code, name, dimension…" /></div>
        {isAdmin && (
          <button onClick={() => setModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-teal-700 hover:bg-teal-600 text-white rounded-lg text-sm shrink-0">
            <Plus className="w-4 h-4" /> Add UOM
          </button>
        )}
      </div>
      <Table
        columns={[
          { key: 'canonical_code', label: 'Code', render: (v) => <code className="text-teal-300 text-xs font-bold">{v}</code> },
          { key: 'name', label: 'Name' },
          { key: 'dimension', label: 'Dimension', render: (v) => <span className="text-gray-400">{v}</span> },
          { key: 'aliases', label: 'Aliases', render: (v: any[]) => <span className="text-gray-500 text-xs">{(v || []).join(', ') || '—'}</span> },
          { key: 'base_multiplier', label: 'Multiplier', render: (v) => <span className="font-mono text-xs text-gray-400">{v}</span> },
          { key: 'status', label: 'Status', render: (v) => <StatusBadge status={v || 'ACTIVE'} /> },
        ]}
        rows={filtered}
      />
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Add UOM">
        <Field label="Canonical Code"><Input value={form.canonical_code} onChange={v => setForm(f => ({ ...f, canonical_code: v }))} placeholder="kg" /></Field>
        <Field label="Name"><Input value={form.name} onChange={v => setForm(f => ({ ...f, name: v }))} placeholder="kilogram" /></Field>
        <Field label="Dimension"><Input value={form.dimension} onChange={v => setForm(f => ({ ...f, dimension: v }))} placeholder="MASS" /></Field>
        <Field label="Aliases (comma-separated)"><Input value={form.aliases} onChange={v => setForm(f => ({ ...f, aliases: v }))} placeholder="kilogram, kgs" /></Field>
        <Field label="Base Multiplier"><Input value={form.base_multiplier} onChange={v => setForm(f => ({ ...f, base_multiplier: v }))} /></Field>
        {err && <p className="text-red-400 text-xs">{err}</p>}
        <SaveBtn onClick={submit} label="Register UOM" />
      </Modal>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Section: Synonyms
// ──────────────────────────────────────────────────────────────────────────────

function SynonymsSection({ headers, isAdmin }: { headers: any; isAdmin: boolean }) {
  const [synonyms, setSynonyms] = useState<any[]>([]);
  const [filter, setFilter] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ term: '', expansion: '', is_ambiguous: false });
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    try { const r = await axios.get(`${API}/admin/synonyms?limit=200`, { headers }); setSynonyms(r.data); } catch {}
  }, []);
  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    setErr('');
    try {
      await axios.post(`${API}/admin/synonyms`, form, { headers });
      setModalOpen(false); setForm({ term: '', expansion: '', is_ambiguous: false }); load();
    } catch (e: any) { setErr(e.response?.data?.detail || 'Error'); }
  };

  const del = async (id: number) => {
    if (!window.confirm('Delete synonym?')) return;
    await axios.delete(`${API}/admin/synonyms/${id}`, { headers }); load();
  };

  const filtered = synonyms.filter(s => `${s.term} ${s.expansion}`.toLowerCase().includes(filter.toLowerCase()));

  return (
    <div>
      <SectionTitle icon={<BookOpen className="w-5 h-5 text-amber-400" />} title="Synonyms" subtitle={`${synonyms.length} synonym pairs`} />
      <div className="flex gap-3 mb-4">
        <div className="flex-1"><SearchBar value={filter} onChange={setFilter} placeholder="Filter by term or expansion…" /></div>
        <button onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-amber-700 hover:bg-amber-600 text-white rounded-lg text-sm shrink-0">
          <Plus className="w-4 h-4" /> Add
        </button>
      </div>
      <Table
        columns={[
          { key: 'term', label: 'Term', render: (v) => <code className="text-amber-300 text-xs">{v}</code> },
          { key: 'expansion', label: 'Expansion' },
          { key: 'is_ambiguous', label: 'Ambiguous', render: (v) => v ? <Badge text="Yes" color="bg-orange-900/40 text-orange-400 border-orange-700" /> : <Badge text="No" color="bg-gray-800 text-gray-500 border-gray-700" /> },
          { key: 'source', label: 'Source', render: (v) => <span className="text-gray-500 text-xs">{v || 'MANUAL'}</span> },
        ]}
        rows={filtered}
        actions={isAdmin ? (row) => (
          <button onClick={() => del(row.id)} className="p-1 hover:text-red-400 text-gray-600">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        ) : undefined}
      />
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Add Synonym">
        <Field label="Term"><Input value={form.term} onChange={v => setForm(f => ({ ...f, term: v }))} placeholder="kilogram" /></Field>
        <Field label="Expansion"><Input value={form.expansion} onChange={v => setForm(f => ({ ...f, expansion: v }))} placeholder="kg" /></Field>
        <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-300">
          <input type="checkbox" checked={form.is_ambiguous} onChange={e => setForm(f => ({ ...f, is_ambiguous: e.target.checked }))}
            className="w-4 h-4 accent-primary-500" />
          Mark as ambiguous
        </label>
        {err && <p className="text-red-400 text-xs">{err}</p>}
        <SaveBtn onClick={submit} label="Add Synonym" />
      </Modal>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Section: Matching Rules
// ──────────────────────────────────────────────────────────────────────────────

function MatchingRulesSection({ headers, isAdmin }: { headers: any; isAdmin: boolean }) {
  const [rules, setRules] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ rule_name: '', description: '', logic_payload: '{}' });
  const [err, setErr] = useState('');
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { const r = await axios.get(`${API}/admin/matching-rules`, { headers }); setRules(r.data); } catch {}
  }, []);
  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    setErr('');
    try {
      const payload_parsed = JSON.parse(form.logic_payload);
      await axios.post(`${API}/admin/matching-rules`, { ...form, logic_payload: payload_parsed }, { headers });
      setModalOpen(false); load();
    } catch (e: any) {
      setErr(e instanceof SyntaxError ? 'Invalid JSON in logic payload' : (e.response?.data?.detail || 'Error'));
    }
  };

  const toggle = async (rule: any) => {
    await axios.put(`${API}/admin/matching-rules/${rule.rule_id}`, { is_active: !rule.is_active }, { headers });
    load();
  };

  return (
    <div>
      <SectionTitle icon={<GitMerge className="w-5 h-5 text-orange-400" />} title="Matching Rules" subtitle="Configurable matching logic" />
      <div className="flex justify-end mb-4">
        {isAdmin && (
          <button onClick={() => setModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-orange-700 hover:bg-orange-600 text-white rounded-lg text-sm">
            <Plus className="w-4 h-4" /> New Rule
          </button>
        )}
      </div>
      <div className="space-y-2">
        {rules.map(r => (
          <div key={r.rule_id} className="border border-gray-800 rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 bg-gray-800/30 cursor-pointer"
              onClick={() => setExpanded(expanded === r.rule_id ? null : r.rule_id)}>
              <div className="flex items-center gap-3">
                <span className={`w-2 h-2 rounded-full ${r.is_active ? 'bg-green-400' : 'bg-gray-600'}`} />
                <span className="font-medium text-gray-200">{r.rule_name}</span>
                <span className="text-xs text-gray-500">{r.description}</span>
              </div>
              <div className="flex items-center gap-3">
                {isAdmin && (
                  <button onClick={e => { e.stopPropagation(); toggle(r); }}
                    className={`text-xs px-2 py-0.5 rounded border transition-colors ${r.is_active ? 'border-red-700 text-red-400 hover:bg-red-900/30' : 'border-green-700 text-green-400 hover:bg-green-900/30'}`}>
                    {r.is_active ? 'Disable' : 'Enable'}
                  </button>
                )}
                {expanded === r.rule_id ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
              </div>
            </div>
            {expanded === r.rule_id && (
              <div className="px-4 py-3 bg-gray-950/50">
                <pre className="text-xs text-gray-400 overflow-x-auto">{JSON.stringify(r.logic_payload, null, 2)}</pre>
              </div>
            )}
          </div>
        ))}
        {!rules.length && <EmptyState message="No matching rules defined." />}
      </div>
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New Matching Rule">
        <Field label="Rule Name"><Input value={form.rule_name} onChange={v => setForm(f => ({ ...f, rule_name: v }))} /></Field>
        <Field label="Description"><Input value={form.description} onChange={v => setForm(f => ({ ...f, description: v }))} /></Field>
        <Field label="Logic Payload (JSON)">
          <textarea rows={5} value={form.logic_payload} onChange={e => setForm(f => ({ ...f, logic_payload: e.target.value }))}
            className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-xs font-mono resize-none" />
        </Field>
        {err && <p className="text-red-400 text-xs">{err}</p>}
        <SaveBtn onClick={submit} label="Create Rule" />
      </Modal>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Section: Model Registry
// ──────────────────────────────────────────────────────────────────────────────

function ModelRegistrySection({ headers, isAdmin }: { headers: any; isAdmin: boolean }) {
  const [models, setModels] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ model_name: '', model_version: '', provider: 'gemini', task: 'EMBEDDING', embedding_dimension: '' });
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    try { const r = await axios.get(`${API}/admin/model-registry`, { headers }); setModels(r.data); } catch {}
  }, []);
  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    setErr('');
    try {
      await axios.post(`${API}/admin/model-registry`, {
        ...form, embedding_dimension: form.embedding_dimension ? parseInt(form.embedding_dimension) : null,
      }, { headers });
      setModalOpen(false); load();
    } catch (e: any) { setErr(e.response?.data?.detail || 'Error'); }
  };

  const setStatus = async (model_id: string, s: string) => {
    await axios.patch(`${API}/admin/model-registry/${model_id}/status`, { deployment_status: s }, { headers });
    load();
  };

  return (
    <div>
      <SectionTitle icon={<Cpu className="w-5 h-5 text-cyan-400" />} title="Model Registry" subtitle="Track AI model versions and deployment status" />
      <div className="flex justify-end mb-4">
        {isAdmin && (
          <button onClick={() => setModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-cyan-700 hover:bg-cyan-600 text-white rounded-lg text-sm">
            <Plus className="w-4 h-4" /> Register Model
          </button>
        )}
      </div>
      <Table
        columns={[
          { key: 'model_name', label: 'Model', render: (v, row) => <div><div className="font-medium text-gray-200">{v}</div><div className="text-xs text-gray-500">{row.model_version}</div></div> },
          { key: 'provider', label: 'Provider', render: (v) => <Badge text={v} color="bg-cyan-900/40 text-cyan-300 border-cyan-700" /> },
          { key: 'task', label: 'Task', render: (v) => <span className="text-gray-400 text-xs">{v}</span> },
          { key: 'embedding_dimension', label: 'Dim', render: (v) => <span className="font-mono text-xs text-gray-500">{v || '—'}</span> },
          { key: 'deployment_status', label: 'Status', render: (v) => <StatusBadge status={v} /> },
          { key: 'created_at', label: 'Registered', render: (v) => <span className="text-xs text-gray-500">{new Date(v).toLocaleDateString()}</span> },
        ]}
        rows={models}
        actions={isAdmin ? (row) => (
          <select value={row.deployment_status}
            onChange={e => setStatus(row.model_id, e.target.value)}
            className="bg-gray-950 border border-gray-800 rounded px-2 py-0.5 text-xs">
            {['ACTIVE', 'DEPRECATED', 'ARCHIVED'].map(s => <option key={s}>{s}</option>)}
          </select>
        ) : undefined}
      />
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Register Model">
        <Field label="Model Name"><Input value={form.model_name} onChange={v => setForm(f => ({ ...f, model_name: v }))} placeholder="text-embedding-004" /></Field>
        <Field label="Version"><Input value={form.model_version} onChange={v => setForm(f => ({ ...f, model_version: v }))} placeholder="1.0.0" /></Field>
        <Field label="Provider"><Input value={form.provider} onChange={v => setForm(f => ({ ...f, provider: v }))} placeholder="gemini" /></Field>
        <Field label="Task"><Input value={form.task} onChange={v => setForm(f => ({ ...f, task: v }))} placeholder="EMBEDDING" /></Field>
        <Field label="Embedding Dimension (optional)"><Input value={form.embedding_dimension} onChange={v => setForm(f => ({ ...f, embedding_dimension: v }))} placeholder="768" /></Field>
        {err && <p className="text-red-400 text-xs">{err}</p>}
        <SaveBtn onClick={submit} label="Register" />
      </Modal>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Section: Prompt Registry
// ──────────────────────────────────────────────────────────────────────────────

function PromptRegistrySection({ headers, isAdmin }: { headers: any; isAdmin: boolean }) {
  const [prompts, setPrompts] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ task: '', prompt_version: '', prompt_template: '' });
  const [err, setErr] = useState('');
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { const r = await axios.get(`${API}/admin/prompt-registry`, { headers }); setPrompts(r.data); } catch {}
  }, []);
  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    setErr('');
    try {
      await axios.post(`${API}/admin/prompt-registry`, form, { headers });
      setModalOpen(false); load();
    } catch (e: any) { setErr(e.response?.data?.detail || 'Error'); }
  };

  const deactivate = async (id: string) => {
    await axios.patch(`${API}/admin/prompt-registry/${id}/deactivate`, {}, { headers }); load();
  };

  return (
    <div>
      <SectionTitle icon={<FileText className="w-5 h-5 text-indigo-400" />} title="Prompt Registry" subtitle="Versioned prompt templates for AI tasks" />
      <div className="flex justify-end mb-4">
        {isAdmin && (
          <button onClick={() => setModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-700 hover:bg-indigo-600 text-white rounded-lg text-sm">
            <Plus className="w-4 h-4" /> New Prompt
          </button>
        )}
      </div>
      <div className="space-y-2">
        {prompts.map(p => (
          <div key={p.prompt_id} className="border border-gray-800 rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 bg-gray-800/30 cursor-pointer"
              onClick={() => setExpanded(expanded === p.prompt_id ? null : p.prompt_id)}>
              <div className="flex items-center gap-3">
                <span className={`w-2 h-2 rounded-full ${p.is_active ? 'bg-green-400' : 'bg-gray-600'}`} />
                <span className="font-medium text-gray-200">{p.task}</span>
                <code className="text-xs text-indigo-300 bg-indigo-950/50 px-2 py-0.5 rounded">v{p.prompt_version}</code>
              </div>
              <div className="flex items-center gap-3">
                {isAdmin && p.is_active && (
                  <button onClick={e => { e.stopPropagation(); deactivate(p.prompt_id); }}
                    className="text-xs px-2 py-0.5 rounded border border-red-700 text-red-400 hover:bg-red-900/30">
                    Deactivate
                  </button>
                )}
                {expanded === p.prompt_id ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
              </div>
            </div>
            {expanded === p.prompt_id && (
              <div className="px-4 py-3 bg-gray-950/50">
                <pre className="text-xs text-gray-400 whitespace-pre-wrap font-mono">{p.prompt_template}</pre>
              </div>
            )}
          </div>
        ))}
        {!prompts.length && <EmptyState message="No prompt templates registered." />}
      </div>
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Register Prompt">
        <Field label="Task"><Input value={form.task} onChange={v => setForm(f => ({ ...f, task: v }))} placeholder="ATTRIBUTE_EXTRACTION" /></Field>
        <Field label="Version"><Input value={form.prompt_version} onChange={v => setForm(f => ({ ...f, prompt_version: v }))} placeholder="v1.0.0" /></Field>
        <Field label="Template">
          <textarea rows={6} value={form.prompt_template}
            onChange={e => setForm(f => ({ ...f, prompt_template: e.target.value }))}
            className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-xs font-mono resize-none"
            placeholder="Extract attributes from material description: {description}..." />
        </Field>
        {err && <p className="text-red-400 text-xs">{err}</p>}
        <SaveBtn onClick={submit} label="Register Prompt" />
      </Modal>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Section: Audit Log
// ──────────────────────────────────────────────────────────────────────────────

function AuditSection({ headers }: { headers: any }) {
  const [logs, setLogs] = useState<any[]>([]);
  const [summary, setSummary] = useState<{ breakdown: { entity_type: string; count: number }[] }>({ breakdown: [] });
  const [filter, setFilter] = useState({ entity_type: '', actor_id: '' });

  const load = useCallback(async () => {
    try {
      const [la, ls] = await Promise.all([
        axios.get(`${API}/admin/audit?limit=100${filter.entity_type ? `&entity_type=${filter.entity_type}` : ''}${filter.actor_id ? `&actor_id=${filter.actor_id}` : ''}`, { headers }),
        axios.get(`${API}/admin/audit/summary`, { headers }),
      ]);
      setLogs(la.data); setSummary(ls.data);
    } catch {}
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  const ACTION_COLORS: Record<string, string> = {
    CREATE: 'bg-green-900/50 text-green-400 border-green-700',
    UPDATE: 'bg-blue-900/50 text-blue-400 border-blue-700',
    DELETE: 'bg-red-900/50 text-red-400 border-red-700',
    DEACTIVATE: 'bg-orange-900/50 text-orange-400 border-orange-700',
    REGISTER: 'bg-purple-900/50 text-purple-400 border-purple-700',
    PUBLISH: 'bg-violet-900/50 text-violet-400 border-violet-700',
    STATUS_CHANGE: 'bg-yellow-900/50 text-yellow-400 border-yellow-700',
  };

  return (
    <div>
      <SectionTitle icon={<ScrollText className="w-5 h-5 text-emerald-400" />} title="Audit Trail" subtitle="Immutable log of all admin changes" />

      {/* Summary chips */}
      <div className="flex flex-wrap gap-2 mb-5">
        {summary.breakdown.map(b => (
          <div key={b.entity_type} className="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-xs">
            <span className="text-gray-400">{b.entity_type}</span>
            <span className="ml-2 text-gray-200 font-bold">{b.count}</span>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <Input value={filter.entity_type} onChange={v => setFilter(f => ({ ...f, entity_type: v }))} placeholder="Filter by entity type…" />
        <Input value={filter.actor_id} onChange={v => setFilter(f => ({ ...f, actor_id: v }))} placeholder="Filter by actor ID…" />
        <button onClick={load} className="p-2 hover:text-gray-200 text-gray-500 transition-colors shrink-0"><RefreshCw className="w-4 h-4" /></button>
      </div>

      <div className="space-y-2">
        {logs.map(e => (
          <div key={e.audit_id} className="flex items-start gap-4 p-3 rounded-lg border border-gray-800 bg-gray-950/40 text-sm">
            <Badge text={e.action || '?'} color={ACTION_COLORS[e.action] ?? 'bg-gray-800 text-gray-400 border-gray-700'} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-gray-300 font-medium">{e.entity_type}</span>
                <code className="text-xs text-gray-500 truncate">{e.entity_id}</code>
              </div>
              <p className="text-gray-600 text-xs mt-0.5">
                {e.actor_id || 'system'} · {new Date(e.timestamp).toLocaleString()} · {e.source || 'api'}
              </p>
            </div>
          </div>
        ))}
        {!logs.length && <EmptyState message="No audit events match the filter." />}
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Placeholder sections (navigate to dedicated pages)
// ──────────────────────────────────────────────────────────────────────────────

function LinkSection({ icon, title, subtitle, to, color }: any) {
  return (
    <a href={to} className="block group">
      <Card className="p-6 hover:border-gray-600 transition-all group-hover:shadow-primary-900/20 group-hover:shadow-lg">
        <div className="flex items-center gap-4">
          <div className={`p-3 rounded-xl border ${color}`}>{icon}</div>
          <div>
            <h3 className="font-semibold text-gray-200 group-hover:text-white transition-colors">{title}</h3>
            <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>
          </div>
          <span className="ml-auto text-gray-600 group-hover:text-gray-300 transition-colors">→</span>
        </div>
      </Card>
    </a>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Main AdminConsole page
// ──────────────────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'users',          label: 'Users',              icon: <Users className="w-4 h-4" /> },
  { id: 'roles',          label: 'Roles',              icon: <Shield className="w-4 h-4" /> },
  { id: 'cpses',          label: 'CPSEs',              icon: <Building2 className="w-4 h-4" /> },
  { id: 'classifications',label: 'Classification',     icon: <FolderTree className="w-4 h-4" /> },
  { id: 'uoms',           label: 'UOM Master',         icon: <Scale className="w-4 h-4" /> },
  { id: 'synonyms',       label: 'Synonyms',           icon: <BookOpen className="w-4 h-4" /> },
  { id: 'matching-rules', label: 'Matching Rules',     icon: <GitMerge className="w-4 h-4" /> },
  { id: 'critical',       label: 'Critical Attrs',     icon: <AlertCircle className="w-4 h-4" /> },
  { id: 'model-registry', label: 'Model Registry',     icon: <Cpu className="w-4 h-4" /> },
  { id: 'prompt-registry',label: 'Prompt Registry',    icon: <FileText className="w-4 h-4" /> },
  { id: 'data-quality',   label: 'Data Quality',       icon: <BarChart3 className="w-4 h-4" /> },
  { id: 'policies',       label: 'Gov. Policies',      icon: <Eye className="w-4 h-4" /> },
  { id: 'audit',          label: 'Audit',              icon: <ScrollText className="w-4 h-4" /> },
  { id: 'data-exports',   label: 'Data Exports',       icon: <Download className="w-4 h-4" /> },
  { id: 'migrations',     label: 'Migrations',         icon: <PackageOpen className="w-4 h-4" /> },
] as const;

type TabId = (typeof TABS)[number]['id'];

export default function AdminConsole() {
  const { token, user } = useAuthStore();
  const isAdmin = (user as any)?.role?.toUpperCase() === 'ADMIN';
  const [activeTab, setActiveTab] = useState<TabId>('users');

  const headers = { Authorization: `Bearer ${token}` };

  const renderContent = () => {
    switch (activeTab) {
      case 'users':           return <UsersSection headers={headers} isAdmin={isAdmin} />;
      case 'roles':           return <RolesSection headers={headers} isAdmin={isAdmin} />;
      case 'cpses':           return <CPSESection headers={headers} isAdmin={isAdmin} />;
      case 'uoms':            return <UOMSection headers={headers} isAdmin={isAdmin} />;
      case 'synonyms':        return <SynonymsSection headers={headers} isAdmin={isAdmin} />;
      case 'matching-rules':  return <MatchingRulesSection headers={headers} isAdmin={isAdmin} />;
      case 'model-registry':  return <ModelRegistrySection headers={headers} isAdmin={isAdmin} />;
      case 'prompt-registry': return <PromptRegistrySection headers={headers} isAdmin={isAdmin} />;
      case 'audit':           return <AuditSection headers={headers} />;
      case 'data-exports':    return <DataExportsSection headers={headers} />;
      case 'migrations':      return <MigrationSection headers={headers} isAdmin={isAdmin} />;

      case 'classifications':
        return (
          <div className="space-y-4">
            <SectionTitle icon={<FolderTree className="w-5 h-5 text-green-400" />} title="Classification Taxonomy" subtitle="Manage the material classification tree" />
            <LinkSection icon={<FolderTree className="w-5 h-5 text-green-400" />} title="Open Taxonomy Manager"
              subtitle="Create, edit, move, deactivate and version classifications" to="/taxonomy"
              color="bg-green-900/40 border-green-800" />
          </div>
        );

      case 'critical':
        return (
          <div className="space-y-4">
            <SectionTitle icon={<AlertCircle className="w-5 h-5 text-red-400" />} title="Critical Attributes & Rules" subtitle="Per-category critical attribute configuration" />
            <LinkSection icon={<AlertCircle className="w-5 h-5 text-red-400" />} title="Open Rule Manager"
              subtitle="Configure critical attributes, thresholds, weights and approval policy" to="/rules"
              color="bg-red-900/40 border-red-800" />
          </div>
        );

      case 'data-quality':
        return (
          <div className="space-y-4">
            <SectionTitle icon={<BarChart3 className="w-5 h-5 text-blue-400" />} title="Data Quality" subtitle="Material data quality metrics and indicators" />
            <div className="grid grid-cols-2 gap-4">
              {[
                { label: 'Overview', path: '/data-quality/overview', desc: 'Platform-wide quality KPIs' },
                { label: 'Materials', path: '/data-quality/materials', desc: 'Per-material quality scores' },
                { label: 'Categories', path: '/data-quality/categories', desc: 'Quality by classification' },
              ].map(l => (
                <LinkSection key={l.label} icon={<BarChart3 className="w-5 h-5 text-blue-400" />} title={l.label}
                  subtitle={l.desc} to={l.path} color="bg-blue-900/40 border-blue-800" />
              ))}
            </div>
          </div>
        );

      case 'policies':
        return (
          <div>
            <SectionTitle icon={<Eye className="w-5 h-5 text-gray-400" />} title="Governance Policies" subtitle="Platform-wide governance rules — no code changes required" />
            <div className="space-y-3">
              {[
                { title: 'Source Material Immutability', desc: 'Source materials are read-only after ingestion. AI modules may not directly modify authoritative records.', status: 'ENFORCED' },
                { title: 'AI Anti-Hallucination Guard', desc: 'LLM explanations may only reference attributes present in the material record. No facts may be introduced from model knowledge alone.', status: 'ENFORCED' },
                { title: 'Canonical Data Governance', desc: 'All writes to NationalMaterial require explicit human approval or auto-approve policy meeting defined score + risk thresholds.', status: 'ENFORCED' },
                { title: 'Retraining Governance', desc: 'Production models may not be retrained without an Admin-approved retraining candidate set. No automatic retraining on feedback.', status: 'ENFORCED' },
                { title: 'Rule Change Versioning', desc: 'Every critical rule and global config change creates a new versioned record and appends an immutable AuditLog entry.', status: 'ENFORCED' },
                { title: 'RBAC Enforcement', desc: 'All write operations require at minimum DATA_STEWARD role. Admin-only operations require ADMIN role. CPSE users cannot modify global rules.', status: 'ENFORCED' },
              ].map(p => (
                <div key={p.title} className="flex items-start gap-4 p-4 border border-gray-800 rounded-lg bg-gray-950/30">
                  <CheckCircle className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-200">{p.title}</h4>
                    <p className="text-xs text-gray-500 mt-1">{p.desc}</p>
                  </div>
                  <Badge text={p.status} color="bg-green-900/40 text-green-400 border-green-700" />
                </div>
              ))}
            </div>
            <div className="mt-5 p-4 bg-yellow-900/20 border border-yellow-800 rounded-lg text-xs text-yellow-400">
              <strong>Note:</strong> Governance policies are enforced at the API and schema layers. To change a policy, a code review and admin deployment is required.
              These policies are not configurable at runtime to prevent privilege escalation.
            </div>
          </div>
        );

      default:
        return <EmptyState message="Select a section." />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900/50 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary-400 to-violet-400">
              Admin & Governance
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Platform configuration, user management, and governance controls
            </p>
          </div>
          {!isAdmin && (
            <div className="flex items-center gap-2 px-4 py-2 bg-yellow-900/30 border border-yellow-800 rounded-lg text-yellow-400 text-sm">
              <Lock className="w-4 h-4" /> Viewing in read-only mode
            </div>
          )}
        </div>
      </div>

      <div className="flex h-[calc(100vh-73px)]">
        {/* Sidebar nav */}
        <nav className="w-52 shrink-0 border-r border-gray-800 bg-gray-900/30 py-4 overflow-y-auto">
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id as TabId)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-all text-left ${
                activeTab === t.id
                  ? 'bg-primary-900/50 text-primary-300 border-r-2 border-primary-500'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/30'
              }`}
            >
              <span className={activeTab === t.id ? 'text-primary-400' : ''}>{t.icon}</span>
              {t.label}
            </button>
          ))}
        </nav>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6">
          <Card className="p-6">
            {renderContent()}
          </Card>
        </main>
      </div>
    </div>
  );
}
