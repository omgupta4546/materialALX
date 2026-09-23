import { apiClient } from './apiClient';

// ── Types ──────────────────────────────────────────────────────────────────────
export interface ClassificationBreadcrumb {
  classification_id: string;
  code: string;
  name: string;
  level: number;
}

export interface NationalMaterialRead {
  national_material_id: string;
  national_material_code: string;
  canonical_description: string;
  classification_id: string | null;
  canonical_uom: string | null;
  status: string;
  version: number;
  provenance: Record<string, any> | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  is_retired: boolean;
  classification_breadcrumb: ClassificationBreadcrumb[];
  source_count: number;
  cpse_count: number;
  attributes: Record<string, any> | null;
}

export interface CpseMappingRow {
  mapping_id: string; // The schema doesn't specify exactly what mappings summary has, but it's likely similar.
  source_material_id: string;
  cpse_code: string;
  legacy_material_code: string;
  description: string;
  uom: string | null;
  mapping_type: string;
  confidence: number | null;
  status: string;
}

export interface AuditEvent {
  action: string;
  user_id: string | null;
  timestamp: string | null;
  details: Record<string, any> | null;
}

export interface NationalMaterialDetail extends NationalMaterialRead {
  mappings_summary: Record<string, any>[];
  audit_history: Record<string, any>[];
}

export interface PaginatedNationalMaterialsFull {
  items: NationalMaterialRead[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface NationalMaterialsParams {
  search?: string;
  classification_id?: string;
  status?: string;
  cpse_id?: string;
  sort_by?: string;
  sort_dir?: string;
  limit?: number;
  offset?: number;
}



// ── API functions ───────────────────────────────────────────────────────────────
export const getNationalMaterialsFn = async (params: NationalMaterialsParams): Promise<PaginatedNationalMaterialsFull> => {
  const response = await apiClient.get<PaginatedNationalMaterialsFull>('/national-materials', { params });
  return response.data;
};

export const getNationalMaterialDetailFn = async (idOrCode: string): Promise<NationalMaterialDetail> => {
  const response = await apiClient.get<NationalMaterialDetail>(`/national-materials/${idOrCode}`);
  return response.data;
};



export interface NationalMaterialCreate {
  canonical_description: string;
  classification_id?: string;
  canonical_uom?: string;
  attributes?: Record<string, any>;
  provenance?: Record<string, any>;
  created_by?: string;
}

export const createNationalMaterialFn = async (payload: NationalMaterialCreate): Promise<NationalMaterialRead> => {
  const response = await apiClient.post<NationalMaterialRead>('/national-materials', payload);
  return response.data;
};

export interface NationalMaterialUpdate {
  canonical_description?: string;
  classification_id?: string;
  canonical_uom?: string;
  attributes?: Record<string, any>;
  provenance?: Record<string, any>;
  editor_id?: string;
}

export const updateNationalMaterialFn = async (id: string, payload: NationalMaterialUpdate): Promise<NationalMaterialRead> => {
  const response = await apiClient.put<NationalMaterialRead>(`/national-materials/${id}`, payload);
  return response.data;
};

export const retireNationalMaterialFn = async (id: string, reason?: string): Promise<{ national_material_id: string; status: string }> => {
  const response = await apiClient.post(`/national-materials/${id}/retire`, { reason, actor_id: 'DEMO_USER' });
  return response.data;
};
