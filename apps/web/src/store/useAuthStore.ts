import { create } from 'zustand';
import { User } from 'firebase/auth';

export type Role = 'data_lead' | 'merchandiser' | 'store_manager' | 'viewer';

export interface AuthState {
  user: User | null;
  brandId: string | null;
  storeId: string | null; // null if brand-level role
  role: Role | null;
  isLoading: boolean;
  setAuth: (user: User | null, brandId: string | null, role: Role | null, storeId: string | null) => void;
  setLoading: (loading: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  brandId: null,
  storeId: null,
  role: null,
  isLoading: true,
  setAuth: (user, brandId, role, storeId) => set({ user, brandId, role, storeId, isLoading: false }),
  setLoading: (isLoading) => set({ isLoading }),
  logout: () => set({ user: null, brandId: null, role: null, storeId: null, isLoading: false }),
}));
