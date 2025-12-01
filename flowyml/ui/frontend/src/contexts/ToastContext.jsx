import React, { createContext, useContext, useState, useCallback } from 'react';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const ToastContext = createContext();

export function ToastProvider({ children }) {
    const [toasts, setToasts] = useState([]);

    const addToast = useCallback((message, type = 'info', duration = 5000) => {
        const id = Date.now() + Math.random();
        setToasts(prev => [...prev, { id, message, type, duration }]);

        if (duration > 0) {
            setTimeout(() => {
                removeToast(id);
            }, duration);
        }
    }, []);

    const removeToast = useCallback((id) => {
        setToasts(prev => prev.filter(toast => toast.id !== id));
    }, []);

    const success = useCallback((message, duration) => addToast(message, 'success', duration), [addToast]);
    const error = useCallback((message, duration) => addToast(message, 'error', duration), [addToast]);
    const warning = useCallback((message, duration) => addToast(message, 'warning', duration), [addToast]);
    const info = useCallback((message, duration) => addToast(message, 'info', duration), [addToast]);

    return (
        <ToastContext.Provider value={{ success, error, warning, info, addToast }}>
            {children}
            <ToastContainer toasts={toasts} onRemove={removeToast} />
        </ToastContext.Provider>
    );
}

export function useToast() {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within ToastProvider');
    }
    return context;
}

function ToastContainer({ toasts, onRemove }) {
    return (
        <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
            <AnimatePresence>
                {toasts.map(toast => (
                    <Toast
                        key={toast.id}
                        toast={toast}
                        onRemove={() => onRemove(toast.id)}
                    />
                ))}
            </AnimatePresence>
        </div>
    );
}

function Toast({ toast, onRemove }) {
    const { message, type } = toast;

    const config = {
        success: {
            icon: CheckCircle,
            bgClass: 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800',
            iconClass: 'text-emerald-600 dark:text-emerald-400',
            textClass: 'text-emerald-900 dark:text-emerald-100'
        },
        error: {
            icon: AlertCircle,
            bgClass: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
            iconClass: 'text-red-600 dark:text-red-400',
            textClass: 'text-red-900 dark:text-red-100'
        },
        warning: {
            icon: AlertTriangle,
            bgClass: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800',
            iconClass: 'text-amber-600 dark:text-amber-400',
            textClass: 'text-amber-900 dark:text-amber-100'
        },
        info: {
            icon: Info,
            bgClass: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
            iconClass: 'text-blue-600 dark:text-blue-400',
            textClass: 'text-blue-900 dark:text-blue-100'
        }
    };

    const { icon: Icon, bgClass, iconClass, textClass } = config[type] || config.info;

    return (
        <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: 100, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className={`pointer-events-auto ${bgClass} border rounded-lg shadow-lg p-4 pr-12 max-w-md relative`}
        >
            <div className="flex items-start gap-3">
                <Icon className={`${iconClass} shrink-0 mt-0.5`} size={20} />
                <p className={`${textClass} text-sm font-medium leading-relaxed`}>
                    {message}
                </p>
            </div>
            <button
                onClick={onRemove}
                className={`absolute top-3 right-3 ${iconClass} hover:opacity-70 transition-opacity`}
            >
                <X size={16} />
            </button>
        </motion.div>
    );
}
