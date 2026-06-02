"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchWithAuth } from "@/lib/api";
import { User, AlertTriangle, CheckCircle } from "lucide-react";
import { use } from "react";

const mockRooms = [
  { id: 1, status: 'empty', duration: 0 },
  { id: 2, status: 'occupied', duration: 3, normal: true },
  { id: 3, status: 'occupied', duration: 1, normal: true },
  { id: 4, status: 'warning', duration: 8, normal: false, message: 'Needs assistance' },
  { id: 5, status: 'empty', duration: 0 },
];

export function generateStaticParams() {
  return [{ id: '123' }];
}

export default function StoreDashboard({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  
  const { data, isLoading } = useQuery({
    queryKey: ['storeStatus', resolvedParams.id],
    queryFn: () => fetchWithAuth(`/api/v1/store/${resolvedParams.id}/status`).catch(() => ({ rooms: mockRooms })),
    refetchInterval: 60000, // Real-time polling every 60s
  });

  if (isLoading) return <div className="p-8 animate-pulse text-gray-500">Loading store dashboard...</div>;

  const rooms = data?.rooms || mockRooms;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Store #{resolvedParams.id}</h1>
          <p className="text-gray-500 dark:text-gray-400">Live Fitting Room Status</p>
        </div>
        <div className="text-sm px-4 py-1.5 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-full flex items-center gap-2 font-medium shadow-sm w-max">
          <span className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]"></span>
          Live Feed
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {rooms.map((room: any) => (
          <div key={room.id} className={`p-6 rounded-2xl border-2 flex flex-col items-center text-center transition-all ${
            room.status === 'empty' ? 'border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800' :
            room.status === 'warning' ? 'border-red-400 bg-red-50 dark:border-red-500/50 dark:bg-red-900/20 shadow-[0_0_15px_rgba(239,68,68,0.2)]' :
            'border-blue-400 bg-blue-50 dark:border-blue-500/50 dark:bg-blue-900/20'
          }`}>
            <h3 className="font-semibold text-lg mb-3 text-gray-700 dark:text-gray-300">Room #{room.id}</h3>
            
            {room.status === 'empty' ? (
              <div className="flex flex-col items-center text-gray-400">
                <CheckCircle size={36} className="mb-2 opacity-50" />
                <span className="font-medium">Empty</span>
              </div>
            ) : room.status === 'warning' ? (
              <div className="flex flex-col items-center text-red-600 dark:text-red-400">
                <AlertTriangle size={36} className="mb-2 animate-bounce drop-shadow-md" />
                <span className="font-extrabold text-lg">Warning</span>
                <span className="text-sm mt-1 font-medium bg-red-200/50 dark:bg-red-900/50 px-2 py-0.5 rounded-md">{room.duration} min+</span>
              </div>
            ) : (
              <div className="flex flex-col items-center text-blue-600 dark:text-blue-400">
                <User size={36} className="mb-2" />
                <span className="font-bold">In Use</span>
                <span className="text-sm mt-1 font-medium">{room.duration} min</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {rooms.some((r: any) => r.status === 'warning') && (
        <div className="bg-red-50 border-l-4 border-red-500 text-red-800 dark:bg-red-900/20 dark:text-red-300 p-4 rounded-r-xl flex items-center gap-4 shadow-sm animate-in slide-in-from-bottom-4">
          <AlertTriangle className="flex-shrink-0 w-6 h-6 text-red-500" />
          <p className="font-semibold">Action Required: A customer needs assistance in a warning room!</p>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6 mt-8">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border dark:border-gray-700">
          <h2 className="text-lg font-bold mb-5 text-gray-900 dark:text-white">Today's Store KPI</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b dark:border-gray-700">
              <span className="text-gray-500 font-medium">Try-ons</span>
              <span className="font-black text-2xl text-gray-900 dark:text-white">142</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b dark:border-gray-700">
              <span className="text-gray-500 font-medium">Conversion Rate</span>
              <span className="font-black text-2xl text-gray-900 dark:text-white flex items-center gap-2">
                28% 
                <span className="text-red-500 text-sm font-bold bg-red-100 dark:bg-red-900/30 px-2 py-0.5 rounded-full">↓3%</span>
              </span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-gray-500 font-medium">Avg Duration</span>
              <span className="font-black text-2xl text-gray-900 dark:text-white">6.2 min</span>
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-indigo-50 to-blue-50 dark:from-indigo-900/20 dark:to-blue-900/20 p-6 rounded-xl shadow-sm border border-indigo-100 dark:border-indigo-800/50">
          <h2 className="text-lg font-bold mb-2 flex items-center gap-2 text-indigo-900 dark:text-indigo-300">
            🛡️ Shield Data (My Contribution)
          </h2>
          <p className="text-sm text-indigo-700/80 dark:text-indigo-400 mb-6 font-medium">This data proves your direct impact on store performance.</p>
          <div className="space-y-3">
            <div className="flex justify-between items-center bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm p-4 rounded-xl shadow-sm">
              <span className="text-gray-700 dark:text-gray-300 font-semibold">Conversion after Assistance</span>
              <span className="font-black text-2xl text-green-600 dark:text-green-400">42%</span>
            </div>
            <div className="flex justify-between items-center bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm p-4 rounded-xl">
              <span className="text-gray-600 dark:text-gray-400 font-medium">No Assistance Conversion</span>
              <span className="font-bold text-xl text-gray-500">22%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
