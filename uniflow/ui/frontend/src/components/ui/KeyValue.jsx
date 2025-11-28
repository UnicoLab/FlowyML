import React from 'react';

export function KeyValue({ label, value, icon, className = '', valueClassName = '' }) {
    return (
        <div className={`flex items-start justify-between p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-700 ${className}`}>
            <div className="flex items-center gap-2">
                {icon && <span className="text-slate-400">{icon}</span>}
                <span className="text-sm font-medium text-slate-600 dark:text-slate-400">{label}</span>
            </div>
            <span className={`text-sm font-mono font-semibold text-slate-900 dark:text-white text-right ${valueClassName}`}>
                {value}
            </span>
        </div>
    );
}

export function KeyValueGrid({ items, columns = 2, className = '' }) {
    return (
        <div className={`grid grid-cols-1 md:grid-cols-${columns} gap-3 ${className}`}>
            {items.map((item, idx) => (
                <KeyValue key={idx} {...item} />
            ))}
        </div>
    );
}
