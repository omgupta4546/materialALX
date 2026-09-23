import { apiClient } from './apiClient';

export interface Classification {
  classification_id: string;
  code: string;
  name: string;
  description: string;
  level: number;
  status: string;
  parent_id: string | null;
  version: number;
  is_latest: boolean;
}

export interface ClassificationNode extends Classification {
  children: ClassificationNode[];
}

export interface ClassificationCreate {
  code: string;
  name: string;
  parent_id?: string | null;
  description?: string | null;
}

export const getClassificationsFn = async (): Promise<Classification[]> => {
  const response = await apiClient.get<Classification[]>('/classifications');
  return response.data;
};

export const getClassificationTreeFn = async (): Promise<ClassificationNode[]> => {
  const response = await apiClient.get<ClassificationNode[]>('/classifications/tree');
  return response.data;
};

export const createClassificationFn = async (payload: ClassificationCreate): Promise<Classification> => {
  const response = await apiClient.post<Classification>('/classifications', payload);
  return response.data;
};

export const deactivateClassificationFn = async (id: string): Promise<Classification> => {
  const response = await apiClient.post<Classification>(`/classifications/${id}/deactivate`);
  return response.data;
};
