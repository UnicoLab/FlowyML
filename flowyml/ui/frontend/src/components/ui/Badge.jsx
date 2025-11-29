import React from 'react';
import { cn } from '../../utils/cn';

const variants = {
    default: "bg-slate-100 text-slate-800",
    primary: "bg-primary-50 text-primary-700 border border-primary-100",
    success: "bg-emerald-50 text-emerald-700 border border-emerald-100",
    warning: "bg-amber-50 text-amber-700 border border-amber-100",
    danger: "bg-rose-50 text-rose-700 border border-rose-100",
    outline: "bg-transparent border border-slate-200 text-slate-600",
};

export function Badge({ className, variant = "default", children, ...props }) {
    return (
        <span
            className={cn(
                "inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ring-black/5",
                variants[variant],
                className
            )}
            {...props}
        >
            {children}
        </span>
    );
}
