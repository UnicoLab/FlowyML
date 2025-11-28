import React from 'react';
import { Package } from 'lucide-react';
import { motion } from 'framer-motion';
import { PluginManager } from './plugins/PluginManager';

export function Plugins() {
    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1
            }
        }
    };

    const item = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0 }
    };

    return (
        <motion.div
            initial="hidden"
            animate="show"
            variants={container}
            className="space-y-6"
        >
            {/* Header */}
            <motion.div variants={item}>
                <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 bg-gradient-to-br from-purple-600 to-purple-800 rounded-lg">
                        <Package className="text-white" size={24} />
                    </div>
                    <h2 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">Plugins & Integrations</h2>
                </div>
                <p className="text-slate-500 dark:text-slate-400 mt-2">
                    Extend UniFlow with plugins from ZenML, Airflow, and other ecosystems. Browse, install, and manage integrations seamlessly.
                </p>
            </motion.div>

            {/* Plugin Manager */}
            <motion.div variants={item}>
                <PluginManager />
            </motion.div>
        </motion.div>
    );
}
