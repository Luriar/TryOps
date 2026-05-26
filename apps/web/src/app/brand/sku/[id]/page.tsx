"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchWithAuth } from "@/lib/api";
import { use } from "react";
import { ArrowRight, Info, AlertTriangle } from "lucide-react";

export default function SkuDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);

  const { data, isLoading } = useQuery({
    queryKey: ['skuDetail', resolvedParams.id],
    queryFn: () => fetchWithAuth(`/api/v1/brand/sku/${resolvedParams.id}`).catch(() => ({
      tryOn: 87,
      tryOnPrevAvg: 75,
      tryOnTrend: 16, // +16%
      conversion: 24,
      conversionAvg: 31,
      conversionTrend: -7, // -7%p
      hesitation: 0.78,
      companion: 12, // 12%
    })),
  });

  if (isLoading) return <div className="p-8 animate-pulse text-gray-500">Loading SKU details...</div>;

  const stats = data || {};

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">SKU: {resolvedParams.id}</h1>
        <p className="text-gray-500 dark:text-gray-400">Detailed Performance Analysis</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border dark:border-gray-700 hover:border-indigo-200 transition-colors">
          <p className="text-sm text-gray-500 font-medium">Try-ons (Daily)</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black dark:text-white">{stats.tryOn}</span>
            <span className={`text-sm font-bold px-2 py-0.5 rounded-md ${stats.tryOnTrend > 0 ? 'bg-green-100 text-green-700 dark:bg-green-900/30' : 'bg-red-100 text-red-700 dark:bg-red-900/30'}`}>
              {stats.tryOnTrend > 0 ? '↑' : '↓'}{Math.abs(stats.tryOnTrend)}%
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1 font-medium">Prev Avg: {stats.tryOnPrevAvg}</p>
        </div>

        <div className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border dark:border-gray-700 hover:border-indigo-200 transition-colors">
          <p className="text-sm text-gray-500 font-medium">Conversion</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black dark:text-white">{stats.conversion}%</span>
            <span className={`text-sm font-bold px-2 py-0.5 rounded-md ${stats.conversionTrend > 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700 dark:bg-red-900/30'}`}>
              {stats.conversionTrend > 0 ? '↑' : '↓'}{Math.abs(stats.conversionTrend)}%p
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1 font-medium">Avg: {stats.conversionAvg}%</p>
        </div>

        <div className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border dark:border-gray-700 hover:border-red-200 transition-colors">
          <p className="text-sm text-gray-500 font-medium">Hesitation Score</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-red-600 dark:text-red-400">{stats.hesitation}</span>
            <span className="text-sm font-bold bg-red-100 text-red-700 dark:bg-red-900/30 px-2 py-0.5 rounded-md">High</span>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border dark:border-gray-700 hover:border-indigo-200 transition-colors">
          <p className="text-sm text-gray-500 font-medium">Companion Effect</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black dark:text-white">{stats.companion}%</span>
            <span className="text-sm text-gray-500 font-medium">Average</span>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border dark:border-gray-700 mt-6">
        <h2 className="text-lg font-bold mb-5 flex items-center gap-2 text-gray-900 dark:text-white">
          <Info size={20} className="text-indigo-500" />
          Hesitation Pattern Analysis
        </h2>
        
        <div className="space-y-4 mb-6">
          <div className="flex items-center gap-4 bg-gray-50 dark:bg-gray-900/50 p-4 rounded-xl border dark:border-gray-700/50">
            <div className="flex-1">
              <p className="font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                M size Try-on <ArrowRight className="w-4 h-4 text-gray-400" /> 5 min later L size Try-on <ArrowRight className="w-4 h-4 text-gray-400" /> Drop off
              </p>
            </div>
            <div className="font-black text-xl text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 px-3 py-1 rounded-lg">38%</div>
          </div>
          <div className="flex items-center gap-4 bg-gray-50 dark:bg-gray-900/50 p-4 rounded-xl border dark:border-gray-700/50">
            <div className="flex-1">
              <p className="font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                Single size 8 min+ retention <ArrowRight className="w-4 h-4 text-gray-400" /> Drop off
              </p>
            </div>
            <div className="font-black text-xl text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 px-3 py-1 rounded-lg">22%</div>
          </div>
        </div>

        <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800/50 p-6 rounded-xl">
          <h3 className="font-bold text-indigo-900 dark:text-indigo-300 flex items-center gap-2 mb-4">
            <AlertTriangle size={18} />
            Recommended Actions
          </h3>
          <ol className="list-decimal list-inside space-y-3 text-indigo-800 dark:text-indigo-400 font-medium">
            <li className="pl-2">Review sizing guide (Gap between M and L)</li>
            <li className="pl-2">Reinforce store manager assistance protocols</li>
          </ol>
          <div className="mt-6 flex gap-3">
            <button className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-lg font-semibold transition-colors shadow-sm">
              Accept Action
            </button>
            <button className="bg-white dark:bg-gray-800 border dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 px-5 py-2.5 rounded-lg font-semibold transition-colors shadow-sm">
              Ignore
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
