"use client";

import { useAuthStore } from "@/store/useAuthStore";
import { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Store, LogOut } from "lucide-react";
import { auth } from "@/lib/firebase";

export function AppLayout({ children }: { children: ReactNode }) {
  const role = useAuthStore((state) => state.role);
  const storeId = useAuthStore((state) => state.storeId);
  const pathname = usePathname();

  // Do not show layout wrapper on login page
  if (pathname === '/login' || pathname === '/') {
    return <>{children}</>;
  }

  const handleLogout = () => {
    auth.signOut();
  };

  return (
    <div className="flex h-screen w-full bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <aside className="w-64 border-r bg-white dark:bg-gray-800 dark:border-gray-700 hidden md:flex flex-col">
        <div className="h-16 flex items-center px-6 border-b dark:border-gray-700">
          <span className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">TryOps</span>
        </div>
        
        <nav className="flex-1 p-4 space-y-2">
          {role !== 'store_manager' && (
            <>
              <Link href="/brand/insights" className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${pathname === '/brand/insights' ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300' : 'hover:bg-gray-100 dark:hover:bg-gray-700'}`}>
                <LayoutDashboard size={20} />
                <span className="font-medium">Insights</span>
              </Link>
              <Link href="/brand/stores" className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${pathname === '/brand/stores' ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300' : 'hover:bg-gray-100 dark:hover:bg-gray-700'}`}>
                <Store size={20} />
                <span className="font-medium">Stores</span>
              </Link>
            </>
          )}

          {role === 'store_manager' && storeId && (
            <Link href={`/store/${storeId}`} className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${pathname.startsWith('/store') ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300' : 'hover:bg-gray-100 dark:hover:bg-gray-700'}`}>
              <Store size={20} />
              <span className="font-medium">My Store</span>
            </Link>
          )}
        </nav>

        <div className="p-4 border-t dark:border-gray-700">
          <button onClick={handleLogout} className="flex items-center gap-3 px-3 py-2 w-full rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400 transition-colors">
            <LogOut size={20} />
            <span className="font-medium">Logout</span>
          </button>
        </div>
      </aside>

      {/* Mobile nav placeholder - will be expanded later */}
      
      <main className="flex-1 overflow-auto bg-gray-50/50 dark:bg-gray-900/50">
        <div className="max-w-7xl mx-auto p-4 md:p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
