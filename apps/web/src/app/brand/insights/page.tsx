"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchWithAuth } from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { AlertCircle } from "lucide-react";

// Mock data since API is not fully implemented
const mockInsights = [
  { message: "SKU_LEGGINGS_M_BLACK: Hesitation 0.78 (High)", type: "warning" },
  { message: "Gangnam Store fitting friction 0.85 (Peak time bottleneck)", type: "alert" },
  { message: "Phantom Try-on 12 cases detected (Suspected missing RFID)", type: "info" }
];

const mockSkuData = [
  { name: "SKU-001", tryOn: 87, conversion: 24, hesitation: 0.78 },
  { name: "SKU-002", tryOn: 65, conversion: 40, hesitation: 0.32 },
  { name: "SKU-003", tryOn: 40, conversion: 35, hesitation: 0.45 },
];

export default function BrandInsightsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['brandInsights'],
    queryFn: () => fetchWithAuth('/api/v1/brand/insights').catch(() => ({ insights: mockInsights, skuData: mockSkuData })),
  });

  if (isLoading) return <div className="p-8 animate-pulse text-gray-500">Loading insights...</div>;

  const insights = data?.insights || mockInsights;
  const skuData = data?.skuData || mockSkuData;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Brand Insights</h1>
        <p className="text-gray-500 dark:text-gray-400">Key metrics across all stores.</p>
      </div>

      <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border dark:border-gray-700">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-white">
          <AlertCircle size={20} className="text-indigo-500" />
          This Week's Core Insights
        </h2>
        <ul className="space-y-3">
          {insights.map((insight: any, i: number) => (
            <li key={i} className="flex items-start gap-2 p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg border dark:border-gray-700/50">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{insight.message}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border dark:border-gray-700">
          <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">High Try-on / Low Conversion</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={skuData}>
                <XAxis dataKey="name" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#888888" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => `${value}%`} />
                <Tooltip cursor={{fill: 'transparent'}} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                <Bar dataKey="conversion" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border dark:border-gray-700">
          <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Store Performance Comparison</h2>
          <div className="h-64 flex items-center justify-center bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-dashed dark:border-gray-700">
            <span className="text-gray-500 font-medium">Heatmap Visualization Placeholder</span>
          </div>
        </div>
      </div>
    </div>
  );
}
