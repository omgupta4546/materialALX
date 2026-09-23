import { apiClient } from './apiClient';

export interface DashboardKPIs {
  total_source_materials: number;
  normalized_materials: number;
  normalization_pct: number;
  duplicate_candidates: number;
  functional_equivalents: number;
  pending_approvals: number;
  approved_mappings: number;
  total_mapped: number;
  mapping_pct: number;
  data_quality_score: number;
  high_risk_matches: number;
  engineering_reviews: number;
  total_matches: number;
}

export const getOverviewFn = async (params?: Record<string, any>): Promise<DashboardKPIs> => {
  const response = await apiClient.get<DashboardKPIs>('/analytics/overview', { params });
  return response.data;
};

export const getMaterialsByCpseFn = async (params?: Record<string, any>): Promise<{ cpse: string; count: number }[]> => {
  const response = await apiClient.get<{ cpse: string; count: number }[]>('/analytics/materials-by-cpse', { params });
  return response.data;
};

export const getUploadCategoriesFn = async (params?: Record<string, any>): Promise<{ status: string; count: number }[]> => {
  const response = await apiClient.get<{ status: string; count: number }[]>('/analytics/upload-categories', { params });
  return response.data;
};

export const getConfidenceDistributionFn = async (params?: Record<string, any>): Promise<{ range: string; count: number }[]> => {
  const response = await apiClient.get<{ range: string; count: number }[]>('/analytics/confidence-distribution', { params });
  return response.data;
};

export const getPendingApprovalsFn = async (params?: Record<string, any>): Promise<{ type: string; count: number }[]> => {
  const response = await apiClient.get<{ type: string; count: number }[]>('/analytics/pending-approvals', { params });
  return response.data;
};

export const getRedundantGroupsFn = async (params?: Record<string, any>): Promise<{ national_code: string; description: string; mapped_count: number; cpse_count: number }[]> => {
  const response = await apiClient.get<{ national_code: string; description: string; mapped_count: number; cpse_count: number }[]>('/analytics/redundant-material-groups', { params });
  return response.data;
};

export const getProcurementOpportunitiesFn = async (params?: Record<string, any>): Promise<{ national_code: string; description: string; total_spend: number; cpse_count: number; order_count: number }[]> => {
  const response = await apiClient.get<{ national_code: string; description: string; total_spend: number; cpse_count: number; order_count: number }[]>('/analytics/procurement-opportunities', { params });
  return response.data;
};

export const getClassificationCoverageFn = async (params?: Record<string, any>): Promise<{ category: string; count: number }[]> => {
  const response = await apiClient.get<{ category: string; count: number }[]>('/analytics/classification-coverage', { params });
  return response.data;
};

export const getDataQualityFn = async (params?: Record<string, any>): Promise<{ avg_completeness: number; avg_uniqueness: number; avg_validity: number; avg_consistency: number }> => {
  const response = await apiClient.get<{ avg_completeness: number; avg_uniqueness: number; avg_validity: number; avg_consistency: number }>('/analytics/data-quality', { params });
  return response.data;
};

export const getProcessingHealthFn = async (params?: Record<string, any>): Promise<{ total_jobs: number; total_records_processed: number; avg_duration_days: number }> => {
  const response = await apiClient.get<{ total_jobs: number; total_records_processed: number; avg_duration_days: number }>('/analytics/processing-health', { params });
  return response.data;
};

export const getRiskDistributionFn = async (params?: Record<string, any>): Promise<{ risk_level: string; count: number }[]> => {
  const response = await apiClient.get<{ risk_level: string; count: number }[]>('/analytics/risk-distribution', { params });
  return response.data;
};

export interface ChartDataPoint { [key: string]: any }

export interface DashboardCharts {
  materials_by_cpse:        { cpse: string; count: number }[];
  upload_by_status:         { status: string; count: number }[];
  confidence_distribution:  { range: string; count: number }[];
  approvals_by_type:        { type: string; count: number }[];
  top_redundant:            { national_code: string; description: string; mapped_count: number; cpse_count: number }[];
  procurement_opportunities:{ national_code: string; description: string; total_spend: number; cpse_count: number; order_count: number }[];
  classification_coverage:  { category: string; count: number }[];
}

export interface RecentUpload {
  id: string; filename: string; status: string; timestamp: string | null;
}
export interface RecentApproval {
  id: string; target_id: string; target_type: string; status: string; approver_id: string | null; timestamp: string | null;
}
export interface RecentJob {
  job_id: string; status: string; records_processed: number; started_at: string | null;
}

export interface DashboardPayload {
  kpis: DashboardKPIs;
  charts: DashboardCharts;
  recent: {
    uploads: RecentUpload[];
    approvals: RecentApproval[];
    jobs: RecentJob[];
  };
}

export const getDashboardFn = async (params?: Record<string, any>): Promise<DashboardPayload> => {
  const [
    kpis,
    materials_by_cpse,
    upload_by_status,
    confidence_distribution,
    approvals_by_type,
    top_redundant,
    procurement_opportunities,
    classification_coverage
  ] = await Promise.all([
    getOverviewFn(params),
    getMaterialsByCpseFn(params),
    getUploadCategoriesFn(params),
    getConfidenceDistributionFn(params),
    getPendingApprovalsFn(params),
    getRedundantGroupsFn(params),
    getProcurementOpportunitiesFn(params),
    getClassificationCoverageFn(params)
  ]);

  // Fetch recent activity feeds
  let uploads: RecentUpload[] = [];
  let approvals: RecentApproval[] = [];
  let jobs: RecentJob[] = [];
  try {
    const [uploadsRes, approvalsRes, jobsRes] = await Promise.all([
      apiClient.get<RecentUpload[]>('/analytics/recent-uploads').catch(() => ({ data: [] as RecentUpload[] })),
      apiClient.get<RecentApproval[]>('/analytics/recent-approvals').catch(() => ({ data: [] as RecentApproval[] })),
      apiClient.get<RecentJob[]>('/analytics/recent-jobs').catch(() => ({ data: [] as RecentJob[] })),
    ]);
    uploads = uploadsRes.data;
    approvals = approvalsRes.data;
    jobs = jobsRes.data;
  } catch { /* graceful fallback */ }

  return {
    kpis,
    charts: {
      materials_by_cpse,
      upload_by_status,
      confidence_distribution,
      approvals_by_type: approvals_by_type.map(a => ({ ...a, status: 'PENDING' })),
      top_redundant,
      procurement_opportunities,
      classification_coverage
    },
    recent: { uploads, approvals, jobs }
  };
};


