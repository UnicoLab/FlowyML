import React, { useState } from 'react';
import { Search, LayoutGrid, List, Table as TableIcon, ArrowUpDown, Filter } from 'lucide-react';
import { Button } from './Button';

export function DataView({
    title,
    subtitle,
    actions,
    items = [],
    columns = [],
    renderGrid,
    renderList,
    searchPlaceholder = "Search...",
    initialView = 'grid',
    emptyState,
    loading = false
}) {
    const [view, setView] = useState(initialView);
    const [searchQuery, setSearchQuery] = useState('');
    const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

    // Filter items
    const filteredItems = items.filter(item => {
        if (!searchQuery) return true;
        const searchStr = searchQuery.toLowerCase();
        return Object.values(item).some(val =>
            String(val).toLowerCase().includes(searchStr)
        );
    });

    // Sort items
    const sortedItems = [...filteredItems].sort((a, b) => {
        if (!sortConfig.key) return 0;

        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];

        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
    });

    const handleSort = (key) => {
        setSortConfig(current => ({
            key,
            direction: current.key === key && current.direction === 'asc' ? 'desc' : 'asc'
        }));
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{title}</h1>
                    {subtitle && <p className="text-slate-500 dark:text-slate-400 mt-1">{subtitle}</p>}
                </div>
                {actions && <div className="flex gap-2">{actions}</div>}
            </div>

            {/* Controls */}
            <div className="flex flex-col md:flex-row gap-4 items-center justify-between bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
                <div className="relative w-full md:w-96">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
                    <input
                        type="text"
                        placeholder={searchPlaceholder}
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm text-slate-900 dark:text-white"
                    />
                </div>

                <div className="flex items-center gap-2 w-full md:w-auto justify-end">
                    <div className="flex bg-slate-100 dark:bg-slate-900 p-1 rounded-lg border border-slate-200 dark:border-slate-700">
                        <button
                            onClick={() => setView('grid')}
                            className={`p-2 rounded-md transition-all ${view === 'grid' ? 'bg-white dark:bg-slate-800 shadow-sm text-primary-600' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                            title="Grid View"
                        >
                            <LayoutGrid size={18} />
                        </button>
                        <button
                            onClick={() => setView('list')}
                            className={`p-2 rounded-md transition-all ${view === 'list' ? 'bg-white dark:bg-slate-800 shadow-sm text-primary-600' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                            title="List View"
                        >
                            <List size={18} />
                        </button>
                        <button
                            onClick={() => setView('table')}
                            className={`p-2 rounded-md transition-all ${view === 'table' ? 'bg-white dark:bg-slate-800 shadow-sm text-primary-600' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                            title="Table View"
                        >
                            <TableIcon size={18} />
                        </button>
                    </div>
                </div>
            </div>

            {/* Content */}
            {loading ? (
                <div className="flex justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
                </div>
            ) : sortedItems.length === 0 ? (
                emptyState || (
                    <div className="text-center py-12 bg-slate-50 dark:bg-slate-800/50 rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700">
                        <div className="flex justify-center mb-4">
                            <Search className="w-12 h-12 text-slate-300 dark:text-slate-600" />
                        </div>
                        <h3 className="text-lg font-medium text-slate-900 dark:text-white">No items found</h3>
                        <p className="text-slate-500 dark:text-slate-400 mt-1">
                            {searchQuery ? `No results matching "${searchQuery}"` : "Get started by creating a new item."}
                        </p>
                    </div>
                )
            ) : (
                <div className="animate-in fade-in duration-300">
                    {view === 'grid' && (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {sortedItems.map((item, idx) => (
                                <div key={idx}>{renderGrid(item)}</div>
                            ))}
                        </div>
                    )}

                    {view === 'list' && (
                        <div className="space-y-4">
                            {sortedItems.map((item, idx) => (
                                <div key={idx}>{renderList ? renderList(item) : renderGrid(item)}</div>
                            ))}
                        </div>
                    )}

                    {view === 'table' && (
                        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm text-left">
                                    <thead className="text-xs text-slate-500 uppercase bg-slate-50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-700">
                                        <tr>
                                            {columns.map((col, idx) => (
                                                <th
                                                    key={idx}
                                                    className="px-6 py-3 font-medium cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                                                    onClick={() => col.sortable && handleSort(col.key)}
                                                >
                                                    <div className="flex items-center gap-2">
                                                        {col.header}
                                                        {col.sortable && <ArrowUpDown size={14} className="text-slate-400" />}
                                                    </div>
                                                </th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                                        {sortedItems.map((item, idx) => (
                                            <tr key={idx} className="bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                                                {columns.map((col, colIdx) => (
                                                    <td key={colIdx} className="px-6 py-4">
                                                        {col.render ? col.render(item) : item[col.key]}
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
