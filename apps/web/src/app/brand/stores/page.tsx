import Link from 'next/link';

export default function BrandStoresPage() {
  const stores = [
    { id: '123', name: 'Gangnam Flagship', status: 'Active', todayTryOns: 142 },
    { id: '456', name: 'Hongdae Store', status: 'Active', todayTryOns: 89 },
    { id: '789', name: 'Myeongdong Store', status: 'Offline', todayTryOns: 0 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Store Management</h1>
        <button className="bg-indigo-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-indigo-700 transition-colors">
          + Add Store
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-900 border-b dark:border-gray-700 text-gray-500 dark:text-gray-400">
              <th className="p-4 font-medium">Store ID</th>
              <th className="p-4 font-medium">Name</th>
              <th className="p-4 font-medium">Status</th>
              <th className="p-4 font-medium">Today's Try-ons</th>
              <th className="p-4 font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {stores.map((store) => (
              <tr key={store.id} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors">
                <td className="p-4 font-medium text-gray-900 dark:text-gray-100">#{store.id}</td>
                <td className="p-4 font-semibold text-gray-800 dark:text-gray-200">{store.name}</td>
                <td className="p-4">
                  <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                    store.status === 'Active' 
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
                      : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                  }`}>
                    {store.status}
                  </span>
                </td>
                <td className="p-4 text-gray-600 dark:text-gray-400">{store.todayTryOns}</td>
                <td className="p-4">
                  <Link 
                    href={`/store/${store.id}`} 
                    className="text-indigo-600 dark:text-indigo-400 font-medium hover:underline"
                  >
                    View Dashboard
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
