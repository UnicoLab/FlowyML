import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';

export function Card({ className, children, hover = true, ...props }) {
    return (
        <motion.div
            whileHover={hover ? { y: -2, boxShadow: "0 10px 30px -10px rgba(0,0,0,0.1)" } : {}}
            transition={{ duration: 0.2 }}
            className={cn(
                "bg-white rounded-xl border border-slate-100 shadow-sm p-6",
                "transition-colors duration-200",
                className
            )}
            {...props}
        >
            {children}
        </motion.div>
    );
}

export function CardHeader({ className, children, ...props }) {
    return (
        <div className={cn("flex flex-col space-y-1.5 mb-4", className)} {...props}>
            {children}
        </div>
    );
}

export function CardTitle({ className, children, ...props }) {
    return (
        <h3 className={cn("font-semibold leading-none tracking-tight text-slate-900", className)} {...props}>
            {children}
        </h3>
    );
}

export function CardContent({ className, children, ...props }) {
    return (
        <div className={cn("", className)} {...props}>
            {children}
        </div>
    );
}
