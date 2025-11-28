import React from 'react';
import { Button } from './Button';

export function EmptyState({
    icon: Icon,
    title,
    description,
    action,
    actionLabel,
    onAction,
    className = ''
}) {
    return (
        <div className={`flex flex-col items-center justify-center py-16 px-4 text-center ${className}`}>
            <div className="w-20 h-20 bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-700 rounded-2xl flex items-center justify-center mb-6 shadow-inner">
                {Icon && <Icon className="text-slate-400 dark:text-slate-500" size={40} />}
            </div>

            <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
                {title}
            </h3>

            {description && (
                <p className="text-slate-500 dark:text-slate-400 max-w-md mb-6">
                    {description}
                </p>
            )}

            {(action || (actionLabel && onAction)) && (
                <div>
                    {action || (
                        <Button onClick={onAction}>
                            {actionLabel}
                        </Button>
                    )}
                </div>
            )}
        </div>
    );
}

// Card wrapper variant
export function EmptyStateCard(props) {
    return (
        <div className="bg-slate-50 dark:bg-slate-800/30 rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700">
            <EmptyState {...props} />
        </div>
    );
}
