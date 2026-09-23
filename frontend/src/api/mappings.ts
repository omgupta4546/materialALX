import { apiClient } from './apiClient';

export interface MaterialMappingRead {
  mapping_id: string;
  source_material_id: string;
  national_material_id: string;
  match_type: string;
  confidence: number | null;
  mapping_status: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedMappings {
  items: MaterialMappingRead[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface MappingsParams {
  cpse_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export const getMappingsFn = async (params: MappingsParams = {}): Promise<PaginatedMappings> => {
  const response = await apiClient.get<PaginatedMappings>('/mappings', { params });
  return response.data;
};

export const getMappingDetailFn = async (id: string): Promise<MaterialMappingRead> => {
  const response = await apiClient.get<MaterialMappingRead>(`/mappings/${id}`);
  return response.data;
};

export interface MappingCreate {
  source_material_id: string;
  national_material_id: string;
  match_type?: string;
  confidence?: number;
  notes?: string;
}

export const createMappingFn = async (payload: MappingCreate): Promise<MaterialMappingRead> => {
  const response = await apiClient.post<MaterialMappingRead>('/mappings', payload);
  return response.data;
};
