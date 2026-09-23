import { apiClient } from './apiClient';

export interface SourceMaterialSummary {
  source_material_id: string;
  cpse_id: string;
  legacy_material_code: string;
  raw_description: string | null;
  raw_uom: string | null;
  raw_category: string | null;
  manufacturer: string | null;
  manufacturer_part_number: string | null;
  plant: string | null;
  source_system: string | null;
  source_file: string | null;
  created_at: string;
  normalized_description: string | null;
  canonical_uom: string | null;
  classification_id: string | null;
  normalization_version: string | null;
  confidence: number | null;
  national_material_id: string | null;
  national_material_code: string | null;
  mapping_status: 'MAPPED' | 'UNMAPPED';
  mapping_type: string | null;
  semantic_score: number | null;
}

export interface SourceMaterialDetail extends SourceMaterialSummary {
  raw_specification: string | null;
  source_record_reference: string | null;
  normalized_manufacturer: string | null;
  normalized_mpn: string | null;
  normalization_method: string | null;
  attributes: Record<string, any> | null;
  embedding_ready: boolean;
  national_description: string | null;
  audit_history?: {
    action: string;
    user_id: string | null;
    timestamp: string | null;
    details: Record<string, any> | null;
  }[];
}

export interface PaginatedSourceMaterials {
  items: SourceMaterialSummary[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
  search_mode?: 'keyword' | 'semantic' | 'none';
  query?: string | null;
}

export interface MaterialsParams {
  cpse_id?: string;
  legacy_code?: string;   // partial match on legacy_material_code
  mpn?: string;           // partial match on manufacturer_part_number
  raw_category?: string;
  manufacturer?: string;
  raw_uom?: string;
  mapping_status?: 'MAPPED' | 'UNMAPPED';
  classification_id?: string;
  q?: string;             // keyword search (maps to backend ?q=)
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
  semantic?: boolean;
}

export const getMaterialsFn = async (params: MaterialsParams): Promise<PaginatedSourceMaterials> => {
  const response = await apiClient.get<PaginatedSourceMaterials>('/materials', { params });
  return response.data;
};

export const getMaterialDetailFn = async (sourceId: string): Promise<SourceMaterialDetail> => {
  const response = await apiClient.get<SourceMaterialDetail>(`/materials/${sourceId}`);
  return response.data;
};

/** Matches CPSERead returned by GET /api/v1/cpses */
export interface Cpse {
  cpse_id: string;        // UUID — use as filter value
  cpse_code: string;      // short code e.g. "NEC"
  cpse_name: string;
  sector: string | null;
  status: string;
}

export const getCpsesFn = async (): Promise<Cpse[]> => {
  const response = await apiClient.get<Cpse[]>('/cpses');
  return response.data;
};
