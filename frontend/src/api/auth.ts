import { apiClient } from './apiClient';

export interface LoginPayload {
  username: string;
  password?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  user_id: string;
  name: string;
  role: string;
  cpse: string | null;
  permissions: string[];
}

export const loginFn = async (payload: LoginPayload): Promise<LoginResponse> => {
  const response = await apiClient.post<LoginResponse>('/auth/login', payload);
  return response.data;
};

export const getMeFn = async (): Promise<UserResponse> => {
  const response = await apiClient.get<UserResponse>('/auth/me');
  return response.data;
};

export const logoutFn = async (): Promise<void> => {
  await apiClient.post('/auth/logout');
};
