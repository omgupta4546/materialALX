import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getMatchesFn, getMatchDetailFn, approveMatchFn, rejectMatchFn, engineeringReviewFn, type MatchSummary, type ReviewActionRequest } from '../api/matches';
import { cn } from '../components/common/MetricCard';
import { CheckCircle2, XCircle, AlertTriangle, Scale, RefreshCw, Info, FileText } from 'lucide-react';

const RiskBadge: React.FC<{ level: string }> = ({ level }) => {
  const cfg: Record<string, string> = {
    LOW: 'text-green-400 bg-green-500/10 border-green-500/20',
    MEDIUM: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    HIGH: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
    CRITICAL: 'text-red-400 bg-red-500/10 border-red-500/20 animate-pulse',
  };
  return <span className={cn('px-2 py-0.5 rounded text-xs font-semibold border', cfg[level] ?? 'text-muted-foreground')}>{level}</span>;
};

export const Approvals: React.FC = () => {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [notes, setNotes] = useState('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Fetch pending matches
  const { data: queue, isLoading: queueLoading } = useQuery({
    queryKey: ['approvals-queue'],
    queryFn: () => getMatchesFn({ decision: 'PENDING', limit: 100 }),
  });

  // Fetch detail for selected match
  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ['match-detail', selectedId],
    queryFn: () => getMatchDetailFn(selectedId!),
    enabled: !!selectedId,
  });

  const pendingMatches = queue?.items || [];

  // Auto-select first item if none selected
  React.useEffect(() => {
    if (!selectedId && pendingMatches.length > 0) {
      setSelectedId(pendingMatches[0].match_id);
    }
  }, [pendingMatches, selectedId]);

  const afterAction = () => {
    qc.invalidateQueries({ queryKey: ['approvals-queue'] });
    qc.invalidateQueries({ queryKey: ['matches'] });
    qc.invalidateQueries({ queryKey: ['analytics-overview'] });
    setActionLoading(null);
    setNotes('');
    // Select next item
    const idx = pendingMatches.findIndex(m => m.match_id === selectedId);
    if (idx >= 0 && idx + 1 < pendingMatches.length) {
      setSelectedId(pendingMatches[idx + 1].match_id);
    } else {
      setSelectedId(null);
    }
  };

  const doAction = async (type: 'approve' | 'reject' | 'engineering-review') => {
    if (!selectedId) return;
    setActionLoading(type);
    const payload: ReviewActionRequest = { comment: notes, reviewer_id: 'DEMO_USER' };
    try {
      if (type === 'approve') await approveMatchFn(selectedId, payload);
      else if (type === 'reject') await rejectMatchFn(selectedId, payload);
      else await engineeringReviewFn(selectedId, payload);
      afterAction();
    } catch { setActionLoading(null); }
  };

  if (queueLoading) {
    return (
      <div className="flex items-center justify-center h-[70vh] text-muted-foreground">
        <RefreshCw size={24} className="animate-spin mr-3" /><span>Loading approval queue...</span>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-6rem)] flex flex-col -mx-4 -mb-4 lg:-mx-8 lg:-mb-8">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border bg-card flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2"><Scale size={20} className="text-primary"/> Approval Queue</h1>
          <p className="text-sm text-muted-foreground mt-0.5">{pendingMatches.length} mappings pending your review</p>
        </div>
      </div>

      {/* Split Pane */}
      <div className="flex flex-1 overflow-hidden">
        
        {/* Left: Queue List */}
        <div className="w-1/3 border-r border-border bg-background/50 flex flex-col overflow-y-auto">
          {pendingMatches.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              <CheckCircle2 size={40} className="mx-auto mb-3 opacity-20" />
              <p>Queue is empty! All caught up.</p>
            </div>
          ) : (
            <div className="p-2 space-y-1">
              {pendingMatches.map((m) => (
                <button
                  key={m.match_id}
                  onClick={() => setSelectedId(m.match_id)}
                  className={cn(
                    "w-full text-left px-4 py-3 rounded-lg border transition-all flex flex-col gap-2",
                    selectedId === m.match_id 
                      ? "bg-primary/10 border-primary/30 ring-1 ring-primary/20" 
                      : "bg-card border-transparent hover:bg-accent hover:border-border"
                  )}
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="text-xs font-semibold text-primary px-2 py-0.5 rounded bg-primary/10">{(m.final_score! * 100).toFixed(0)}% Match</span>
                    <RiskBadge level={m.risk_level || 'LOW'} />
                  </div>
                  <div className="text-sm truncate w-full text-foreground/90 font-medium">
                    {m.match_type?.replace(/_/g, ' ')}
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground w-full">
                    <span>AI: {m.recommendation}</span>
                    <span className="opacity-70">{new Date(m.created_at).toLocaleDateString()}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right: Detail View */}
        <div className="flex-1 bg-card flex flex-col overflow-hidden relative">
          {!selectedId ? (
            <div className="flex-1 flex items-center justify-center text-muted-foreground bg-background/20">
              Select an item from the queue to review
            </div>
          ) : detailLoading ? (
            <div className="flex-1 flex items-center justify-center text-muted-foreground">
              <RefreshCw size={24} className="animate-spin mr-3" /><span>Loading details...</span>
            </div>
          ) : detail ? (
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              
              {/* Scores Header */}
              <div className="grid grid-cols-4 gap-4 p-4 rounded-xl bg-background border border-border">
                 <div className="text-center">
                    <p className="text-xs text-muted-foreground uppercase mb-1">Final Score</p>
                    <p className="text-2xl font-bold text-primary">{(detail.final_score! * 100).toFixed(1)}%</p>
                 </div>
                 <div className="text-center">
                    <p className="text-xs text-muted-foreground uppercase mb-1">Semantic</p>
                    <p className="text-lg font-medium">{(detail.semantic_score! * 100).toFixed(1)}%</p>
                 </div>
                 <div className="text-center">
                    <p className="text-xs text-muted-foreground uppercase mb-1">Attribute</p>
                    <p className="text-lg font-medium">{(detail.attribute_score! * 100).toFixed(1)}%</p>
                 </div>
                 <div className="text-center">
                    <p className="text-xs text-muted-foreground uppercase mb-1">Rule</p>
                    <p className="text-lg font-medium">{(detail.rule_score! * 100).toFixed(1)}%</p>
                 </div>
              </div>

              {/* Side by side comparison */}
              <div className="flex gap-4">
                <div className="flex-1 glass rounded-xl border border-border overflow-hidden">
                  <div className="bg-muted/50 px-4 py-2 border-b border-border font-semibold text-sm">Source Material</div>
                  <div className="p-4 space-y-3 text-sm">
                    <div className="flex gap-2"><span className="text-muted-foreground w-20">Code:</span><span className="font-mono">{detail.material_a?.legacy_material_code}</span></div>
                    <div className="flex gap-2"><span className="text-muted-foreground w-20">Desc:</span><span className="font-medium">{detail.material_a?.raw_description}</span></div>
                    <div className="flex gap-2"><span className="text-muted-foreground w-20">UOM:</span><span>{detail.material_a?.raw_uom}</span></div>
                    <div className="flex gap-2"><span className="text-muted-foreground w-20">CPSE:</span><span>{detail.material_a?.cpse_id}</span></div>
                  </div>
                </div>
                
                <div className="flex flex-col justify-center text-muted-foreground/30"><RefreshCw size={24} /></div>

                <div className="flex-1 glass rounded-xl border border-border overflow-hidden">
                  <div className="bg-primary/5 px-4 py-2 border-b border-border font-semibold text-sm text-primary">National Material (Target)</div>
                  <div className="p-4 space-y-3 text-sm">
                    <div className="flex gap-2"><span className="text-muted-foreground w-20">Code:</span><span className="font-mono text-primary">{detail.material_b?.national_material_code}</span></div>
                    <div className="flex gap-2"><span className="text-muted-foreground w-20">Desc:</span><span className="font-medium">{detail.material_b?.national_description}</span></div>
                    <div className="flex gap-2"><span className="text-muted-foreground w-20">UOM:</span><span>{detail.material_b?.canonical_uom}</span></div>
                    <div className="flex gap-2"><span className="text-muted-foreground w-20">Category:</span><span>{detail.material_b?.classification_id}</span></div>
                  </div>
                </div>
              </div>

              {/* Evidence */}
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-4">
                  <h4 className="text-sm font-semibold text-green-500 flex items-center gap-2 mb-3"><CheckCircle2 size={16}/> Positive Evidence</h4>
                  <pre className="text-xs font-mono text-muted-foreground overflow-auto">
                    {JSON.stringify(detail.positive_evidence, null, 2)}
                  </pre>
                </div>
                <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4">
                  <h4 className="text-sm font-semibold text-red-500 flex items-center gap-2 mb-3"><AlertTriangle size={16}/> Conflicts / Negative</h4>
                  <pre className="text-xs font-mono text-muted-foreground overflow-auto">
                    {JSON.stringify(detail.conflicts || detail.negative_evidence, null, 2)}
                  </pre>
                </div>
              </div>

            </div>
          ) : null}

          {/* Action Footer */}
          {selectedId && detail && (
            <div className="p-4 border-t border-border bg-card/80 backdrop-blur shrink-0 space-y-4">
              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 block">Reviewer Notes (Optional)</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add justification for your decision..."
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary h-16 resize-none"
                />
              </div>
              
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => doAction('reject')}
                  disabled={!!actionLoading}
                  className="px-4 py-2 rounded-lg text-sm font-semibold bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {actionLoading === 'reject' ? <RefreshCw size={16} className="animate-spin" /> : <XCircle size={16} />}
                  Reject Match
                </button>
                <button
                  onClick={() => doAction('engineering-review')}
                  disabled={!!actionLoading}
                  className="px-4 py-2 rounded-lg text-sm font-semibold bg-blue-500/10 text-blue-500 hover:bg-blue-500/20 transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {actionLoading === 'engineering-review' ? <RefreshCw size={16} className="animate-spin" /> : <Info size={16} />}
                  Escalate
                </button>
                <button
                  onClick={() => doAction('approve')}
                  disabled={!!actionLoading}
                  className="px-5 py-2 rounded-lg text-sm font-semibold bg-green-500 hover:bg-green-600 text-white shadow-lg transition-all disabled:opacity-50 flex items-center gap-2"
                >
                  {actionLoading === 'approve' ? <RefreshCw size={16} className="animate-spin" /> : <CheckCircle2 size={16} />}
                  Approve Mapping
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
