"use client";

import { useEffect, useState } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '@/lib/firebase';
import { useAuthStore, Role } from '@/store/useAuthStore';
import { useRouter, usePathname } from 'next/navigation';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const setAuth = useAuthStore((state) => state.setAuth);
  const setLoading = useAuthStore((state) => state.setLoading);
  const isLoading = useAuthStore((state) => state.isLoading);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_USE_MOCK_DATA === 'true') {
      const checkMockAuth = () => {
        const role = localStorage.getItem("mock_auth_role");
        if (role) {
          const mockUser = {
            uid: 'mock-uid',
            email: 'mock@tryops.com',
            getIdTokenResult: async () => ({
              claims: { role, brand_id: 'brand1', store_id: role === 'store_manager' ? '123' : null }
            })
          } as any;
          
          const storeId = role === 'store_manager' ? '123' : null;
          setAuth(mockUser, 'brand1', role as Role, storeId);
          
          if (pathname === '/login' || pathname === '/') {
            router.replace(role === 'store_manager' ? `/store/${storeId}` : '/brand/insights');
          }
        } else {
          setAuth(null, null, null, null);
          if (pathname !== '/login') router.replace('/login');
        }
      };
      
      checkMockAuth();
      window.addEventListener("storage", checkMockAuth);
      return () => window.removeEventListener("storage", checkMockAuth);
    }

    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        // Fetch custom claims from Firebase Token
        const token = await user.getIdTokenResult();
        const role = (token.claims.role as Role) || 'viewer'; // default fallback
        const brandId = (token.claims.brand_id as string) || 'default_brand';
        const storeId = (token.claims.store_id as string) || null;

        setAuth(user, brandId, role, storeId);
        
        // RBAC Routing Logic
        if (pathname === '/login' || pathname === '/') {
          if (role === 'store_manager' && storeId) {
            router.replace(`/store/${storeId}`);
          } else {
            router.replace('/brand/insights');
          }
        }
      } else {
        setAuth(null, null, null, null);
        if (pathname !== '/login') {
          router.replace('/login');
        }
      }
    });

    return () => unsubscribe();
  }, [setAuth, setLoading, router, pathname]);

  if (isLoading) {
    return <div className="flex h-screen w-screen items-center justify-center bg-gray-50 dark:bg-gray-900">Loading...</div>;
  }

  return <>{children}</>;
}
