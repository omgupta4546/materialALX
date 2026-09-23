import { apiClient } from './apiClient';

// ── Canonical match type values (MatchResult.match_type) ───────────────────────
export type MatchType =
  | 'EXACT_DUPLICATE'
  | 'NEAR_DUPLICATE'
  | 'FUNCTIONALLY_EQUIVALENT'
  | 'RELATED'
  | 'NOT_EQUIVALENT'
  | 'REQUIRES_ENGINEERING_REVIEW';

// ── Canonical approval decision values (Approval.decision DB CHECK) ────────────
export type ApprovalDecision = 'APPROVED' | 'REJECTED' | 'ESCALATED';

// ── Match Summary (list view) ──────────────────────────────────────────────────
export interface MatchSummary {
  match_id: string;
  material_a_id: string;
  material_b_id: string;

  // AI-generated scores (immutable — never mutated by human action)
  final_score: number | null;
  semantic_score: number | null;
  attribute_score: number | null;
  rule_score: number | null;

  match_type: MatchType | null;
  recommendation: string | null;
  risk_level: string | null;
  requires_human_review: boolean;
  model_version: string | null;
  created_at: string;
  
  // Denormalised latest human decision (stored separately from AI result)
  decision: ApprovalDecision | null;
  review_type: string | null;
  reviewer_id: string | null;
  decided_at: string | null;
}

export interface PaginatedMatches {
  items: MatchSummary[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

// ── Detail ─────────────────────────────────────────────────────────────────────
export interface MaterialSnapshot {
  source_material_id: string | null;
  cpse_id: string | null;
  legacy_material_code: string | null;
  raw_description: string | null;
  raw_uom: string | null;
  manufacturer: string | null;
  manufacturer_part_number: string | null;
  normalized_description: string | null;
  canonical_uom: string | null;
  classification_id: string | null;
  confidence: number | null;
  national_material_id: string | null;
  national_material_code: string | null;
  national_description: string | null;
}

export interface ApprovalRead {
  approval_id: string;
  match_id: string;
  reviewer_id: string | null;
  decision: ApprovalDecision;
  comment: string | null;
  review_type: string | null;
  created_at: string;
}

export interface MatchDetail extends MatchSummary {
  positive_evidence: Record<string, any>;
  negative_evidence: Record<string, any>;
  conflicts: Record<string, any>;
  prompt_version: string | null;
  rules_version: string | null;
  material_a: MaterialSnapshot | null;
  material_b: MaterialSnapshot | null;
  review_history: ApprovalRead[];
}

export interface MatchesParams {
  /** 'PENDING' means no human decision yet — translated to null+requires_review on the wire. */
  decision?: 'APPROVED' | 'REJECTED' | 'ESCALATED' | 'PENDING';
  match_type?: MatchType;
  min_score?: number;
  requires_review?: boolean;
  sort_by?: 'final_score' | 'semantic_score' | 'created_at';
  sort_dir?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

// ── Action request / response ─────────────────────────────────────────────────
export interface ReviewActionRequest {
  comment?: string;     // backend field is 'comment'
  reviewer_id?: string;
  review_type?: string;
}

export interface ReviewActionResponse {
  match_id: string;
  approval_id: string;
  decision: ApprovalDecision;
  reviewer_id: string;
  comment: string | null;
  created_at: string;
}

// ── API Functions ──────────────────────────────────────────────────────────────

export const getMatchesFn = async (params: MatchesParams): Promise<PaginatedMatches> => {
  // Backend natively supports decision=PENDING (filters for null approval)
  const response = await apiClient.get<PaginatedMatches>('/matches', { params });
  return response.data;
};

export const getMatchDetailFn = async (matchId: string): Promise<MatchDetail> => {
  const response = await apiClient.get<MatchDetail>(`/matches/${matchId}`);
  return response.data;
};

/** Approve: stores Approval(decision=APPROVED). AI MatchResult is untouched. */
export const approveMatchFn = async (
  matchId: string,
  body: ReviewActionRequest
): Promise<ReviewActionResponse> => {
  const response = await apiClient.post<ReviewActionResponse>(`/matches/${matchId}/approve`, body);
  return response.data;
};

/** Reject: stores Approval(decision=REJECTED). AI MatchResult is untouched. */
export const rejectMatchFn = async (
  matchId: string,
  body: ReviewActionRequest
): Promise<ReviewActionResponse> => {
  const response = await apiClient.post<ReviewActionResponse>(`/matches/${matchId}/reject`, body);
  return response.data;
};

/** Engineering Review: stores Approval(decision=ESCALATED, review_type=ENGINEERING_REVIEW). */
export const engineeringReviewFn = async (
  matchId: string,
  body: ReviewActionRequest
): Promise<ReviewActionResponse> => {
  const response = await apiClient.post<ReviewActionResponse>(
    `/matches/${matchId}/engineering-review`,
    body
  );
  return response.data;
};
