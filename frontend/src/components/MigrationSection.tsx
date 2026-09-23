import React, { useState, useEffect } from 'react';
import { PlayCircle, CheckCircle, XCircle, RotateCcw, AlertTriangle, PackageOpen, Loader2 } from 'lucide-react';
import { Card } from './Card';
import { Badge } from './Badge';

export function MigrationSection({ headers, isAdmin }: { headers: any, isAdmin: boolean }) {
  const [batches, setBatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchBatches = async () => {
    setLoading(true);
    try {
      const token = headers.Authorization.split(' ')[1];
      const res = await fetch('http://localhost:8000/api/v1/migration/batches', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) setBatches(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBatches();
  }, []);

  const handleAction = async (batchId: string, action: string) => {
    if (!isAdmin && action !== 'validate') {
      alert("Only Admins can perform this action.");
      return;
    }
    setActionLoading(`${batchId}-${action}`);
    try {
      const token = headers.Authorization.split(' ')[1];
      const res = await fetch(`http://localhost:8000/api/v1/migration/batches/${batchId}/${action}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) {
        const err = await res.json();
        alert(`Action failed: ${err.detail || 'Unknown error'}`);
      } else {
        fetchBatches();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'DRAFT': return 'bg-gray-500/20 text-gray-400 border-gray-600';
      case 'VALIDATED': return 'bg-blue-500/20 text-blue-400 border-blue-600';
      case 'APPROVED': return 'bg-indigo-500/20 text-indigo-400 border-indigo-600';
      case 'READY': return 'bg-yellow-500/20 text-yellow-400 border-yellow-600';
      case 'EXECUTED': return 'bg-green-500/20 text-green-400 border-green-600';
      case 'ROLLED_BACK': return 'bg-orange-500/20 text-orange-400 border-orange-600';
      case 'FAILED': return 'bg-red-500/20 text-red-400 border-red-600';
      default: return 'bg-gray-500/20 text-gray-400';
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4 border-b border-gray-800 pb-4">
        <div className="flex items-center gap-2">
          <PackageOpen className="w-5 h-5 text-green-400" />
          <div>
            <h2 className="text-lg font-medium text-gray-200">Migration Workflow</h2>
            <p className="text-sm text-gray-500">Manage batched legacy-to-national material migrations.</p>
          </div>
        </div>
        <button onClick={fetchBatches} className="px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 rounded text-gray-200">
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="text-center py-8 text-gray-500"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
      ) : batches.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No migration batches found.</div>
      ) : (
        <div className="grid gap-4">
          {batches.map(batch => (
            <Card key={batch.batch_id} className="p-4 bg-gray-900 border-gray-800 flex justify-between items-center">
              <div>
                <h3 className="font-medium text-gray-200">{batch.name}</h3>
                <p className="text-sm text-gray-500 mt-1">
                  ID: <span className="font-mono">{batch.batch_id.split('-')[0]}</span> • 
                  Records: {batch.record_count} • 
                  Created: {new Date(batch.created_at).toLocaleString()}
                </p>
                <div className="mt-2">
                  <Badge className={getStatusColor(batch.status)}>{batch.status}</Badge>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {batch.status === 'DRAFT' && (
                  <button onClick={() => handleAction(batch.batch_id, 'validate')} disabled={!!actionLoading} className="px-3 py-1.5 text-sm bg-blue-900/30 text-blue-400 border border-blue-800 rounded hover:bg-blue-900/50">
                    {actionLoading === `${batch.batch_id}-validate` ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Validate'}
                  </button>
                )}
                {batch.status === 'VALIDATED' && isAdmin && (
                  <button onClick={() => handleAction(batch.batch_id, 'approve')} disabled={!!actionLoading} className="px-3 py-1.5 text-sm bg-indigo-900/30 text-indigo-400 border border-indigo-800 rounded hover:bg-indigo-900/50">
                    {actionLoading === `${batch.batch_id}-approve` ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Approve'}
                  </button>
                )}
                {(batch.status === 'APPROVED' || batch.status === 'READY') && isAdmin && (
                  <button onClick={() => handleAction(batch.batch_id, 'execute')} disabled={!!actionLoading} className="flex items-center gap-1 px-3 py-1.5 text-sm bg-green-900/30 text-green-400 border border-green-800 rounded hover:bg-green-900/50">
                    {actionLoading === `${batch.batch_id}-execute` ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />} Execute
                  </button>
                )}
                {batch.status === 'EXECUTED' && isAdmin && (
                  <button onClick={() => handleAction(batch.batch_id, 'rollback')} disabled={!!actionLoading} className="flex items-center gap-1 px-3 py-1.5 text-sm bg-orange-900/30 text-orange-400 border border-orange-800 rounded hover:bg-orange-900/50">
                    {actionLoading === `${batch.batch_id}-rollback` ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />} Rollback
                  </button>
                )}
                
                {batch.status === 'EXECUTED' && (
                  <a href={`http://localhost:8000/api/v1/exports/migration-report?format=csv`} target="_blank" rel="noreferrer" className="flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-800 text-gray-300 border border-gray-700 rounded hover:bg-gray-700">
                    Download Export
                  </a>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
