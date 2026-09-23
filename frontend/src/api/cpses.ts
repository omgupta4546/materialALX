import { apiClient } from './apiClient';

export interface CPSERead {
  cpse_id: string;
  cpse_code: string;
  cpse_name: string;
  sector: string | null;
  description: string | null;
  status: string;
}

export const getCpsesFn = async (): Promise<CPSERead[]> => {
  const response = await apiClient.get<CPSERead[]>('/cpses');
  return response.data;
};
