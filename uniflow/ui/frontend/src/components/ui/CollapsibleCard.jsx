import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export function CollapsibleCard({
    title,
    children,
    icon,
    badge,
    defaultOpen = false,
    className = '',
    headerClassName = ''
}) {
    const [isOpen, setIsOpen] = useState(defaultOpen);

    return (
        <div className={`border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden bg-white dark:bg-slate-800 ${className}`}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`w-full flex items-center justify-between p-4 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors ${headerClassName}`}
            >
                <div className="flex items-center gap-3">
                    {icon && <span className="text-slate-500">{icon}</span>}
                    <h3 className="text-base font-semibold text-slate-900 dark:text-white">{title}</h3>
                    {badge && <span>{badge}</span>}
                </div>
                <div className="flex items-center gap-2">
                    {isOpen ? (
                        <ChevronDown size={18} className="text-slate-400" />
                    ) : (
                        <ChevronRight size={18} className="text-slate-400" />
                    )}
                </div>
            </button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                    >
                        <div className="p-4 pt-0 border-t border-slate-100 dark:border-slate-700">
                            {children}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
