import { create } from 'zustand';
import { getMeFn, logoutFn } from '../api/auth';

export interface User {
  user_id: string;
  name: string;
  role: string;
  cpse: string | null;
  permissions: string[];
}

interface AuthState {
  token: string | null;
  user: User | null;
  isInitializing: boolean;
  setAuth: (token: string, remember: boolean) => Promise<void>;
  logout: () => void;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isInitializing: true,
  setAuth: async (token, remember) => {
    if (remember) {
      localStorage.setItem('auth_token', token);
    } else {
      sessionStorage.setItem('auth_token', token);
    }
    set({ token, isInitializing: true });
    try {
      const user = await getMeFn();
      set({ user, isInitializing: false });
    } catch (error) {
      localStorage.removeItem('auth_token');
      sessionStorage.removeItem('auth_token');
      set({ token: null, user: null, isInitializing: false });
    }
  },
  logout: async () => {
    try {
      await logoutFn();
    } catch (e) {
      // ignore
    }
    localStorage.removeItem('auth_token');
    sessionStorage.removeItem('auth_token');
    set({ token: null, user: null, isInitializing: false });
  },
  initialize: async () => {
    const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
    if (!token) {
      set({ isInitializing: false, token: null, user: null });
      return;
    }

    set({ token, isInitializing: true });
    try {
      const user = await getMeFn();
      set({ user, isInitializing: false });
    } catch (error) {
      localStorage.removeItem('auth_token');
      sessionStorage.removeItem('auth_token');
      set({ token: null, user: null, isInitializing: false });
    }
  }
}));
