import React from 'react';
import { CheckCircle, XCircle, Clock, Loader, AlertCircle, PlayCircle } from 'lucide-react';

const statusConfig = {
    completed: {
        icon: CheckCircle,
        label: 'Completed',
        color: 'text-emerald-600 dark:text-emerald-400',
        bg: 'bg-emerald-50 dark:bg-emerald-900/20',
        border: 'border-emerald-200 dark:border-emerald-800'
    },
    success: {
        icon: CheckCircle,
        label: 'Success',
        color: 'text-emerald-600 dark:text-emerald-400',
        bg: 'bg-emerald-50 dark:bg-emerald-900/20',
        border: 'border-emerald-200 dark:border-emerald-800'
    },
    failed: {
        icon: XCircle,
        label: 'Failed',
        color: 'text-rose-600 dark:text-rose-400',
        bg: 'bg-rose-50 dark:bg-rose-900/20',
        border: 'border-rose-200 dark:border-rose-800'
    },
    running: {
        icon: Loader,
        label: 'Running',
        color: 'text-blue-600 dark:text-blue-400',
        bg: 'bg-blue-50 dark:bg-blue-900/20',
        border: 'border-blue-200 dark:border-blue-800',
        animate: true
    },
    pending: {
        icon: Clock,
        label: 'Pending',
        color: 'text-amber-600 dark:text-amber-400',
        bg: 'bg-amber-50 dark:bg-amber-900/20',
        border: 'border-amber-200 dark:border-amber-800'
    },
    queued: {
        icon: Clock,
        label: 'Queued',
        color: 'text-slate-600 dark:text-slate-400',
        bg: 'bg-slate-50 dark:bg-slate-900/20',
        border: 'border-slate-200 dark:border-slate-700'
    },
    initializing: {
        icon: PlayCircle,
        label: 'Initializing',
        color: 'text-blue-600 dark:text-blue-400',
        bg: 'bg-blue-50 dark:bg-blue-900/20',
        border: 'border-blue-200 dark:border-blue-800'
    },
    cached: {
        icon: CheckCircle,
        label: 'Cached',
        color: 'text-cyan-600 dark:text-cyan-400',
        bg: 'bg-cyan-50 dark:bg-cyan-900/20',
        border: 'border-cyan-200 dark:border-cyan-800'
    }
};

export function ExecutionStatus({
    status,
    size = 'md',
    showLabel = true,
    className = '',
    iconOnly = false
}) {
    const config = statusConfig[status?.toLowerCase()] || statusConfig.pending;
    const Icon = config.icon;

    const sizeClasses = {
        sm: { icon: 14, text: 'text-xs', padding: 'px-2 py-0.5' },
        md: { icon: 16, text: 'text-sm', padding: 'px-2.5 py-1' },
        lg: { icon: 20, text: 'text-base', padding: 'px-3 py-1.5' }
    };

    const { icon: iconSize, text: textSize, padding } = sizeClasses[size];

    if (iconOnly) {
        return (
            <Icon
                size={iconSize}
                className={`${config.color} ${config.animate ? 'animate-spin' : ''} ${className}`}
            />
        );
    }

    return (
        <div className={`inline-flex items-center gap-1.5 ${padding} rounded-full border ${config.bg} ${config.border} ${className}`}>
            <Icon
                size={iconSize}
                className={`${config.color} ${config.animate ? 'animate-spin' : ''}`}
            />
            {showLabel && (
                <span className={`font-medium ${config.color} ${textSize}`}>
                    {config.label}
                </span>
            )}
        </div>
    );
}

// Badge variant for minimal display
export function StatusBadge({ status, className = '' }) {
    return <ExecutionStatus status={status} size="sm" className={className} />;
}

// Icon-only variant
export function StatusIcon({ status, size = 16, className = '' }) {
    const config = statusConfig[status?.toLowerCase()] || statusConfig.pending;
    const Icon = config.icon;

    return (
        <Icon
            size={size}
            className={`${config.color} ${config.animate ? 'animate-spin' : ''} ${className}`}
        />
    );
}
