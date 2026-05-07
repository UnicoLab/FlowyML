import React from 'react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { Cpu, Box, Calendar, Clock, Container, Database, Tag, Cloud, ExternalLink, Globe } from 'lucide-react';
import { motion } from 'framer-motion';

export function RunMetaPanel({ run }) {
    if (!run) return null;

    // ── Extract real resource info from run data ──
    // Resources may be at run.resources or run.docker level
    const resources = run.resources || {};
    const dockerInfo = run.docker || {};
    const isRemote = run.is_remote === true;
    const dashboardUrl = run.dashboard_url;
    const remotePlatform = run.remote_platform;
    const cloudState = run.cloud_state;

    // Parse Docker image to extract registry
    const dockerImage = dockerInfo.image || null;
    let registry = null;
    let imageName = dockerImage;
    if (dockerImage && dockerImage.includes('/')) {
        const parts = dockerImage.split('/');
        // Detect known registry patterns
        if (parts[0].includes('.') || parts[0].includes(':')) {
            registry = parts[0];
            imageName = parts.slice(1).join('/');
        }
    }

    const scheduleInfo = run.trigger ? {
        type: run.trigger.type,
        cron: run.trigger.cron,
        next_run: run.trigger.next_run
    } : null;

    return (
        <Card className="p-4 bg-white/50 dark:bg-slate-800/50 backdrop-blur-sm border border-slate-200 dark:border-slate-700/50 shadow-sm">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Tag size={12} /> Run Environment
                {isRemote && (
                    <Badge variant="secondary" className="ml-2 text-[10px] bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-700 flex items-center gap-1">
                        <Cloud size={10} />
                        {remotePlatform || 'Remote'}
                    </Badge>
                )}
            </h4>

            <div className={`grid grid-cols-1 gap-6 ${isRemote ? 'md:grid-cols-4' : 'md:grid-cols-3'}`}>
                {/* Cloud / Remote Info (only for remote runs) */}
                {isRemote && (
                    <div className="space-y-3">
                        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                            <Cloud size={16} className="text-blue-500" />
                            Cloud Orchestrator
                        </div>
                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-xs">
                                <span className="text-slate-500">Platform</span>
                                <Badge variant="secondary" className="text-[10px] bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-700 uppercase tracking-wide">
                                    {remotePlatform || 'unknown'}
                                </Badge>
                            </div>
                            {cloudState && (
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-slate-500">State</span>
                                    <span className="font-mono text-slate-700 dark:text-slate-200 text-[10px]">
                                        {cloudState.replace('PIPELINE_STATE_', '')}
                                    </span>
                                </div>
                            )}
                            {run.remote_job_id && (
                                <div className="flex flex-col gap-1">
                                    <span className="text-xs text-slate-500">Job ID</span>
                                    <code className="text-[9px] bg-slate-100 dark:bg-slate-700 px-1.5 py-1 rounded text-slate-600 dark:text-slate-300 truncate block" title={run.remote_job_id}>
                                        {run.remote_job_id.split('/').pop()}
                                    </code>
                                </div>
                            )}
                            {dashboardUrl && (
                                <a
                                    href={dashboardUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-1.5 mt-1 px-2.5 py-1.5 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg text-xs font-medium hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors border border-blue-200 dark:border-blue-700"
                                >
                                    <ExternalLink size={12} />
                                    Open Cloud Dashboard
                                </a>
                            )}
                        </div>
                    </div>
                )}

                {/* Resources */}
                <div className="space-y-3">
                    <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                        <Cpu size={16} className="text-blue-500" />
                        Resources
                    </div>
                    <div className="space-y-2">
                        {resources.cpu ? (
                            <div className="flex items-center justify-between text-xs">
                                <span className="text-slate-500">CPU</span>
                                <span className="font-mono text-slate-700 dark:text-slate-200">{resources.cpu}</span>
                            </div>
                        ) : (
                            <div className="flex items-center justify-between text-xs">
                                <span className="text-slate-500">Compute</span>
                                <span className="font-mono text-slate-700 dark:text-slate-200">Default</span>
                            </div>
                        )}
                        {resources.memory ? (
                            <div className="flex items-center justify-between text-xs">
                                <span className="text-slate-500">Memory</span>
                                <span className="font-mono text-slate-700 dark:text-slate-200">{resources.memory}</span>
                            </div>
                        ) : (
                            <div className="flex items-center justify-between text-xs">
                                <span className="text-slate-500">Memory</span>
                                <span className="font-mono text-slate-700 dark:text-slate-200">Default</span>
                            </div>
                        )}
                        {resources.gpu && (
                            <div className="flex items-center justify-between text-xs">
                                <span className="text-slate-500">GPU</span>
                                <Badge variant="secondary" className="text-[10px] bg-purple-50 text-purple-700 border-purple-200">
                                    {resources.gpu_count ? `${resources.gpu_count}x ` : ''}{resources.gpu}
                                </Badge>
                            </div>
                        )}
                        {resources.accelerator_type && (
                            <div className="flex items-center justify-between text-xs">
                                <span className="text-slate-500">Accelerator</span>
                                <Badge variant="secondary" className="text-[10px] bg-purple-50 text-purple-700 border-purple-200">
                                    {resources.accelerator_type}
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
                        {dockerImage ? (
                            <>
                                <div className="flex flex-col gap-1">
                                    <span className="text-xs text-slate-500">Docker Image</span>
                                    <code className="text-[10px] bg-slate-100 dark:bg-slate-700 px-1.5 py-1 rounded text-slate-600 dark:text-slate-300 truncate block" title={dockerImage}>
                                        {imageName}
                                    </code>
                                </div>
                                {registry && (
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-slate-500 w-16">Registry</span>
                                        <span className="text-xs font-medium text-slate-700 dark:text-slate-300 truncate">{registry}</span>
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="flex flex-col gap-1">
                                <span className="text-xs text-slate-500">Runtime</span>
                                <span className="text-xs font-medium text-slate-700 dark:text-slate-300">Local Python Environment</span>
                            </div>
                        )}
                        {dockerInfo.base_image && dockerInfo.base_image !== dockerImage && (
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-slate-500 w-16">Base</span>
                                <code className="text-[10px] bg-slate-100 dark:bg-slate-700 px-1 py-0.5 rounded truncate">{dockerInfo.base_image}</code>
                            </div>
                        )}
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
