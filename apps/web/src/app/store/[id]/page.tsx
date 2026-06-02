import DashboardClient from "./DashboardClient";

export function generateStaticParams() {
  return [{ id: '123' }];
}

export default async function StoreDashboard({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = await params;
  return <DashboardClient storeId={resolvedParams.id} />;
}
