import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Button';

/**
 * Shown when a page could not load its data.
 *
 * Distinct from EmptyState on purpose: rendering "no runs yet" for a failed
 * request tells the user their data is gone when the server is simply
 * unreachable.
 */
export function ErrorState({
    title = 'Could not load data',
    message,
    onRetry,
    className = ''
}) {
    return (
        <div
            role="alert"
            className={`flex flex-col items-center justify-center py-16 px-4 text-center ${className}`}
        >
            <div className="w-20 h-20 bg-rose-100 dark:bg-rose-900/30 rounded-2xl flex items-center justify-center mb-6">
                <AlertTriangle className="text-rose-600 dark:text-rose-400" size={40} />
            </div>

            <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
                {title}
            </h3>

            {message && (
                <p className="text-slate-500 dark:text-slate-400 max-w-md mb-6 break-words">
                    {message}
                </p>
            )}

            {onRetry && (
                <Button onClick={onRetry} variant="secondary" className="flex items-center gap-2">
                    <RefreshCw size={16} />
                    Try again
                </Button>
            )}
        </div>
    );
}
