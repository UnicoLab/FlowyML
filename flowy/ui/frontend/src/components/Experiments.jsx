import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FlaskConical, ArrowRight, Sparkles } from 'lucide-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { format } from 'date-fns';
import { motion } from 'framer-motion';

export function Experiments() {
    const [experiments, setExperiments] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('/api/experiments')
            .then(res => res.json())
            .then(data => {
                setExperiments(data.experiments || []);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: {
                staggerChildren: 0.08
            }
        }
    };

    const item = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0 }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    return (
        <motion.div
            initial="hidden"
            animate="show"
            variants={container}
            className="space-y-8"
        >
            <motion.div variants={item}>
                <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg">
                        <FlaskConical className="text-white" size={24} />
                    </div>
                    <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Experiments</h2>
                </div>
                <p className="text-slate-500 mt-2 flex items-center gap-2">
                    <Sparkles size={16} className="text-purple-400" />
                    Track and compare your ML experiments with detailed metrics and parameters.
                </p>
            </motion.div>

            {experiments.length > 0 ? (
                <motion.div
                    variants={container}
                    className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                >
                    {experiments.map((exp) => (
                        <motion.div key={exp.experiment_id} variants={item}>
                            <Link to={`/experiments/${exp.experiment_id}`}>
                                <Card className="group cursor-pointer hover:border-primary-300 hover:shadow-lg h-full transition-all duration-200 overflow-hidden relative">
                                    <div className="absolute inset-0 bg-gradient-to-br from-purple-50/50 to-pink-50/50 opacity-0 group-hover:opacity-100 transition-opacity duration-200" />

                                    <div className="relative">
                                        <div className="flex items-start justify-between mb-4">
                                            <div className="p-3 bg-purple-50 rounded-xl text-purple-600 group-hover:bg-purple-600 group-hover:text-white transition-all duration-200 group-hover:scale-110">
                                                <FlaskConical size={24} />
                                            </div>
                                            <Badge variant="default" className="bg-slate-100 text-slate-600 group-hover:bg-purple-100 group-hover:text-purple-700 transition-colors">
                                                {exp.run_count || 0} runs
                                            </Badge>
                                        </div>

                                        <h3 className="text-lg font-bold text-slate-900 mb-2 group-hover:text-purple-700 transition-colors">
                                            {exp.name}
                                        </h3>
                                        <p className="text-sm text-slate-500 mb-4 line-clamp-2 min-h-[2.5rem]">
                                            {exp.description || "No description provided"}
                                        </p>

                                        <div className="flex items-center justify-between pt-4 border-t border-slate-100">
                                            <span className="text-xs text-slate-400 font-medium">
                                                {exp.created_at ? format(new Date(exp.created_at), 'MMM d, yyyy') : '-'}
                                            </span>
                                            <span className="text-sm font-semibold text-primary-600 group-hover:text-primary-700 flex items-center gap-1 group-hover:gap-2 transition-all">
                                                View <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                                            </span>
                                        </div>
                                    </div>
                                </Card>
                            </Link>
                        </motion.div>
                    ))}
                </motion.div>
            ) : (
                <motion.div variants={item}>
                    <Card className="p-16 text-center border-dashed border-2 border-slate-200 bg-slate-50/30">
                        <div className="mx-auto w-20 h-20 bg-gradient-to-br from-purple-100 to-pink-100 rounded-2xl flex items-center justify-center mb-6 shadow-inner">
                            <FlaskConical className="text-purple-400" size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-slate-900 mb-2">No experiments yet</h3>
                        <p className="text-slate-500 max-w-md mx-auto mb-6">
                            Start tracking your ML experiments using the Experiment API to compare runs and optimize your models.
                        </p>
                        <div className="inline-block px-4 py-2 bg-slate-100 rounded-lg text-sm font-mono text-slate-600">
                            <code>from flowy.tracking import Experiment</code>
                        </div>
                    </Card>
                </motion.div>
            )}
        </motion.div>
    );
}
