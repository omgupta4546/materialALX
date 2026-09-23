import { apiClient } from './apiClient';

export interface ValidationError {
  row: number;
  error: string;
  severity: string;
  data?: Record<string, any>;
}

export interface UploadResponse {
  job_id: string;
  upload_id: string;
  status: string;
  total_records: number;
  accepted_records: number;
  rejected_records: number;
  validation_errors: ValidationError[];
}

export interface JobRead {
  job_id: string;
  status: string;
  job_type: string;
  current_stage?: string;
  records_processed: number;
  total_records: number;
  successful: number;
  failed: number;
  errors: Record<string, any>;
  details: Record<string, any>;
  started_at: string;
  completed_at?: string;
}

export const uploadFileFn = async (file: File, cpseCode: string): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('cpse_id', cpseCode); // Backend expects cpse_id parameter name

  const response = await apiClient.post<UploadResponse>('/materials/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getJobFn = async (jobId: string): Promise<JobRead> => {
  const response = await apiClient.get<JobRead>(`/jobs/${jobId}`);
  return response.data;
};
