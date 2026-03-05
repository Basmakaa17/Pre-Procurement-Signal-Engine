export function SkeletonCard() {
  return (
    <div className="bg-white rounded-lg p-5 animate-pulse border border-gray-200 shadow-sm">
      <div className="h-4 bg-gray-100 rounded w-3/4 mb-4" />
      <div className="h-3 bg-gray-100 rounded w-1/2 mb-2" />
      <div className="h-3 bg-gray-100 rounded w-2/3" />
    </div>
  );
}

export function SkeletonTable() {
  return (
    <div className="space-y-2">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex gap-4 animate-pulse">
          <div className="h-4 bg-gray-100 rounded flex-1" />
          <div className="h-4 bg-gray-100 rounded w-32" />
          <div className="h-4 bg-gray-100 rounded w-24" />
          <div className="h-4 bg-gray-100 rounded w-20" />
        </div>
      ))}
    </div>
  );
}
