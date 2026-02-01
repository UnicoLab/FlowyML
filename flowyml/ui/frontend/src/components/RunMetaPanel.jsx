import React from 'react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { Cpu, Box, Calendar, Clock, Container, Database, Tag } from 'lucide-react';
import { motion } from 'framer-motion';

export function RunMetaPanel({ run }) {
    if (!run) return null;

    // Simulate getting resource info from run metadata if available, else placeholders
    const resources = run.metadata?.resources || {
        cpu: "Standard (2 vCPU)",
        memory: "8 GiB",
        gpu: run.metadata?.resources?.gpu ? `${run.metadata.resources.gpu_count}x ${run.metadata.resources.gpu}` : null
    };

    const dockerInfo = run.metadata?.docker || {
        image: "flowyml/base:latest",
        registry: "ghcr.io",
        requirements: ["tensorflow", "scikit-learn"]
    };

    const scheduleInfo = run.trigger ? {
        type: run.trigger.type,
        cron: run.trigger.cron,
        next_run: run.trigger.next_run
    } : null;

    return (
        <Card className="p-4 bg-white/50 dark:bg-slate-800/50 backdrop-blur-sm border border-slate-200 dark:border-slate-700/50 shadow-sm">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Tag size={12} /> Run Environment
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Resources */}
                <div className="space-y-3">
                    <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                        <Cpu size={16} className="text-blue-500" />
                        Resources
                    </div>
                    <div className="space-y-2">
                        <div className="flex items-center justify-between text-xs">
                            <span className="text-slate-500">Compute</span>
                            <span className="font-mono text-slate-700 dark:text-slate-200">{resources.cpu}</span>
                        </div>
                        <div className="flex items-center justify-between text-xs">
                            <span className="text-slate-500">Memory</span>
                            <span className="font-mono text-slate-700 dark:text-slate-200">{resources.memory}</span>
                        </div>
                        {resources.gpu && (
                            <div className="flex items-center justify-between text-xs">
                                <span className="text-slate-500">GPU</span>
                                <Badge variant="secondary" className="text-[10px] bg-purple-50 text-purple-700 border-purple-200">
                                    {resources.gpu}
                                </Badge>
                            </div>
                        )}
                    </div>
                </div>

                {/* Docker / Environment */}
                <div className="space-y-3">
                    <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                        <Container size={16} className="text-cyan-500" />
                        Environment
                    </div>
                    <div className="space-y-2">
                        <div className="flex flex-col gap-1">
                            <span className="text-xs text-slate-500">Base Image</span>
                            <code className="text-[10px] bg-slate-100 dark:bg-slate-700 px-1.5 py-1 rounded text-slate-600 dark:text-slate-300 truncate">
                                {dockerInfo.image}
                            </code>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-500 w-16">Registry</span>
                            <span className="text-xs font-medium text-slate-700 dark:text-slate-300 truncate">{dockerInfo.registry}</span>
                        </div>
                    </div>
                </div>

                {/* Schedule / Trigger */}
                <div className="space-y-3">
                    <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                        <Calendar size={16} className="text-emerald-500" />
                        Trigger Info
                    </div>
                    {scheduleInfo ? (
                        <div className="space-y-2">
                            <div className="flex items-center gap-2">
                                <Badge variant="outline" className="text-xs uppercase">{scheduleInfo.type}</Badge>
                                {scheduleInfo.cron && <code className="text-[10px] bg-slate-100 px-1 py-0.5 rounded">{scheduleInfo.cron}</code>}
                            </div>
                            {scheduleInfo.next_run && (
                                <div className="text-xs text-slate-500 flex items-center gap-1">
                                    <Clock size={10} />
                                    Next: {new Date(scheduleInfo.next_run).toLocaleString()}
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="flex items-center gap-2 h-full py-2">
                            <div className="p-1.5 bg-slate-100 rounded-lg">
                                <Box size={14} className="text-slate-400" />
                            </div>
                            <span className="text-xs text-slate-500 italic">Manual Trigger</span>
                        </div>
                    )}
                </div>
            </div>
        </Card>
    );
}
