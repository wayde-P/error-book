export default function Pagination({ page, totalPages, onPageChange }) {
  return (
    <div className="flex items-center justify-center gap-3 mt-6">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page === 1}
        className="px-3 py-1 rounded border text-sm text-gray-600 disabled:opacity-40 hover:bg-gray-50">
        上一页
      </button>
      <span className="text-sm text-gray-600">第 {page} / {totalPages} 页</span>
      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page === totalPages}
        className="px-3 py-1 rounded border text-sm text-gray-600 disabled:opacity-40 hover:bg-gray-50">
        下一页
      </button>
    </div>
  )
}
