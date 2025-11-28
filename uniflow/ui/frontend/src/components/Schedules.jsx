import React, { useState, useEffect } from 'react';
import { Calendar, Play, Pause, Trash2, Plus, Clock, CheckCircle, XCircle, Activity, Globe, History, AlertCircle } from 'lucide-react';
import { format } from 'date-fns';
import { DataView } from './ui/DataView';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { useProject } from '../contexts/ProjectContext';

export default function Schedules() {
    const { selectedProject } = useProject();
    const [schedules, setSchedules] = useState([]);
    const [pipelines, setPipelines] = useState({ registered: [], templates: [], metadata: [] });
    const [health, setHealth] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showHistoryModal, setShowHistoryModal] = useState(false);
    const [selectedSchedule, setSelectedSchedule] = useState(null);
    const [history, setHistory] = useState([]);
    const [historyLoading, setHistoryLoading] = useState(false);

    // Form state
    const [formData, setFormData] = useState({
        name: '',
        pipeline_name: '',
        schedule_type: 'daily',
        hour: 0,
        minute: 0,
        interval_seconds: 3600,
        cron_expression: '* * * * *',
        timezone: 'UTC',
        project_name: selectedProject || null
    });

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 10000); // Refresh every 10s
        return () => clearInterval(interval);
    }, [selectedProject]);

    const fetchData = async () => {
        try {
            const projectParam = selectedProject ? `?project=${selectedProject}` : '';
            const [schedulesRes, pipelinesRes, healthRes] = await Promise.all([
                fetch(`/api/schedules/${projectParam}`),
                fetch(`/api/schedules/registered-pipelines${projectParam}`),
                fetch('/api/schedules/health')
            ]);

            const schedulesData = await schedulesRes.json();
            const pipelinesData = await pipelinesRes.json();

            let healthData = null;
            if (healthRes.ok) {
                healthData = await healthRes.json();
            }

            setSchedules(schedulesData);
            setPipelines(pipelinesData);
            setHealth(healthData);
        } catch (error) {
            console.error('Failed to fetch data:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchHistory = async (scheduleName) => {
        setHistoryLoading(true);
        try {
            const res = await fetch(`/api/schedules/${scheduleName}/history`);
            const data = await res.json();
            setHistory(data);
        } catch (error) {
            console.error('Failed to fetch history:', error);
        } finally {
            setHistoryLoading(false);
        }
    };

    const openHistory = (schedule) => {
        setSelectedSchedule(schedule);
        setShowHistoryModal(true);
        fetchHistory(schedule.pipeline_name);
    };

    const createSchedule = async (e) => {
        e.preventDefault();
        try {
            const response = await fetch('/api/schedules/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                setShowCreateModal(false);
                setFormData({
                    name: '',
                    pipeline_name: '',
                    schedule_type: 'daily',
                    hour: 0,
                    minute: 0,
                    interval_seconds: 3600,
                    cron_expression: '* * * * *',
                    timezone: 'UTC'
                });
                fetchData();
            } else {
                const error = await response.json();
                alert(`Failed to create schedule: ${error.detail}`);
            }
        } catch (error) {
            console.error('Failed to create schedule:', error);
        }
    };

    const toggleSchedule = async (name, enabled) => {
        try {
            const action = enabled ? 'disable' : 'enable';
            await fetch(`/api/schedules/${name}/${action}`, { method: 'POST' });
            fetchData();
        } catch (error) {
            console.error('Failed to toggle schedule:', error);
        }
    };

    const deleteSchedule = async (name) => {
        if (!confirm(`Delete schedule "${name}"?`)) return;
        try {
            await fetch(`/api/schedules/${name}`, { method: 'DELETE' });
            fetchData();
        } catch (error) {
            console.error('Failed to delete schedule:', error);
        }
    };

    const columns = [
        {
            header: 'Pipeline',
            key: 'pipeline_name',
            sortable: true,
            render: (schedule) => (
                <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${schedule.enabled ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-400'}`}>
                        <Clock size={16} />
                    </div>
                    <div>
                        <div className="font-medium text-slate-900 dark:text-white">{schedule.pipeline_name}</div>
                        <div className="text-xs text-slate-500 flex items-center gap-1">
                            <Globe size={10} /> {schedule.timezone}
                        </div>
                    </div>
                </div>
            )
        },
        {
            header: 'Type',
            key: 'schedule_type',
            sortable: true,
            render: (schedule) => (
                <div className="flex flex-col">
                    <Badge variant="secondary" className="capitalize w-fit mb-1">
                        {schedule.schedule_type}
                    </Badge>
                    <span className="text-xs font-mono text-slate-500">
                        {schedule.schedule_value}
                    </span>
                </div>
            )
        },
        {
            header: 'Next Run',
            key: 'next_run',
            sortable: true,
            render: (schedule) => (
                <div className="flex items-center gap-2 text-slate-500">
                    <Calendar size={14} />
                    {schedule.next_run ? format(new Date(schedule.next_run), 'MMM d, HH:mm:ss') : 'N/A'}
                </div>
            )
        },
        {
            header: 'Status',
            key: 'enabled',
            sortable: true,
            render: (schedule) => (
                <div className={`flex items-center gap-2 text-sm ${schedule.enabled ? 'text-emerald-600' : 'text-slate-400'}`}>
                    {schedule.enabled ? <CheckCircle size={14} /> : <XCircle size={14} />}
                    <span className="font-medium">{schedule.enabled ? 'Active' : 'Paused'}</span>
                </div>
            )
        },
        {
            header: 'Actions',
            key: 'actions',
            render: (schedule) => (
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => openHistory(schedule)}
                        className="p-1.5 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors"
                        title="History"
                    >
                        <History size={16} />
                    </button>
                    <button
                        onClick={() => toggleSchedule(schedule.pipeline_name, schedule.enabled)}
                        className={`p-1.5 rounded-lg transition-colors ${schedule.enabled
                            ? 'bg-amber-50 text-amber-600 hover:bg-amber-100'
                            : 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100'
                            }`}
                        title={schedule.enabled ? 'Pause' : 'Resume'}
                    >
                        {schedule.enabled ? <Pause size={16} /> : <Play size={16} />}
                    </button>
                    <button
                        onClick={() => deleteSchedule(schedule.pipeline_name)}
                        className="p-1.5 rounded-lg bg-rose-50 text-rose-600 hover:bg-rose-100 transition-colors"
                        title="Delete"
                    >
                        <Trash2 size={16} />
                    </button>
                </div>
            )
        }
    ];

    const renderGrid = (schedule) => (
        <Card className="group hover:shadow-lg transition-all duration-200 border-l-4 border-l-transparent hover:border-l-primary-500 h-full">
            <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div className={`p-3 rounded-xl ${schedule.enabled ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-400'}`}>
                        <Clock size={24} />
                    </div>
                    <div>
                        <h3 className="font-bold text-slate-900 dark:text-white truncate max-w-[150px]" title={schedule.pipeline_name}>
                            {schedule.pipeline_name}
                        </h3>
                        <div className={`text-xs font-medium flex items-center gap-1 ${schedule.enabled ? 'text-emerald-600' : 'text-slate-400'}`}>
                            {schedule.enabled ? <CheckCircle size={12} /> : <XCircle size={12} />}
                            {schedule.enabled ? 'Active' : 'Paused'}
                        </div>
                    </div>
                </div>
                <Badge variant="secondary" className="capitalize">
                    {schedule.schedule_type}
                </Badge>
            </div>

            <div className="space-y-3 mb-4">
                <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-500 flex items-center gap-2"><Calendar size={14} /> Next Run</span>
                    <span className="font-mono text-slate-700 dark:text-slate-300">
                        {schedule.next_run ? format(new Date(schedule.next_run), 'MMM d, HH:mm') : 'N/A'}
                    </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-500 flex items-center gap-2"><Globe size={14} /> Timezone</span>
                    <span className="text-slate-700 dark:text-slate-300">
                        {schedule.timezone}
                    </span>
                </div>
            </div>

            <div className="flex items-center gap-2 pt-4 border-t border-slate-100 dark:border-slate-700">
                <Button
                    variant="ghost"
                    className="text-blue-600 hover:bg-blue-50 hover:text-blue-700"
                    onClick={() => openHistory(schedule)}
                    title="History"
                >
                    <History size={16} />
                </Button>
                <Button
                    variant="outline"
                    className={`flex-1 flex items-center justify-center gap-2 ${!schedule.enabled ? 'text-emerald-600 border-emerald-200 hover:bg-emerald-50' : 'text-amber-600 border-amber-200 hover:bg-amber-50'}`}
                    onClick={() => toggleSchedule(schedule.pipeline_name, schedule.enabled)}
                >
                    {schedule.enabled ? <><Pause size={14} /> Pause</> : <><Play size={14} /> Resume</>}
                </Button>
                <Button
                    variant="ghost"
                    className="text-rose-600 hover:bg-rose-50 hover:text-rose-700"
                    onClick={() => deleteSchedule(schedule.pipeline_name)}
                >
                    <Trash2 size={16} />
                </Button>
            </div>
        </Card>
    );

    return (
        <div className="p-6 max-w-7xl mx-auto">
            {health && health.metrics && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                    <Card className="p-4 flex items-center gap-4">
                        <div className={`p-3 rounded-full ${health.status === 'running' ? 'bg-emerald-100 text-emerald-600' : 'bg-rose-100 text-rose-600'}`}>
                            <Activity size={24} />
                        </div>
                        <div>
                            <div className="text-sm text-slate-500">Scheduler Status</div>
                            <div className="text-lg font-bold capitalize">{health.status}</div>
                        </div>
                    </Card>
                    <Card className="p-4">
                        <div className="text-sm text-slate-500 mb-1">Total Runs</div>
                        <div className="text-2xl font-bold">{health.metrics.total_runs}</div>
                    </Card>
                    <Card className="p-4">
                        <div className="text-sm text-slate-500 mb-1">Success Rate</div>
                        <div className="text-2xl font-bold text-emerald-600">
                            {(health.metrics.success_rate * 100).toFixed(1)}%
                        </div>
                    </Card>
                    <Card className="p-4">
                        <div className="text-sm text-slate-500 mb-1">Active Schedules</div>
                        <div className="text-2xl font-bold">{health.enabled_schedules} / {health.num_schedules}</div>
                    </Card>
                </div>
            )}

            <DataView
                title="Schedules"
                subtitle="Manage automated pipeline executions"
                items={schedules}
                loading={loading}
                columns={columns}
                renderGrid={renderGrid}
                actions={
                    <Button onClick={() => setShowCreateModal(true)} className="flex items-center gap-2">
                        <Plus size={18} />
                        New Schedule
                    </Button>
                }
                emptyState={
                    <div className="text-center py-16 bg-slate-50 dark:bg-slate-800/30 rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700">
                        <div className="mx-auto w-20 h-20 bg-slate-100 dark:bg-slate-700 rounded-2xl flex items-center justify-center mb-6">
                            <Calendar className="text-slate-400" size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">No active schedules</h3>
                        <p className="text-slate-500 max-w-md mx-auto mb-6">
                            Automate your pipelines by creating a schedule.
                        </p>
                        <Button onClick={() => setShowCreateModal(true)}>
                            Create your first schedule
                        </Button>
                    </div>
                }
            />

            {showCreateModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl w-full max-w-md border border-slate-200 dark:border-slate-700 shadow-2xl animate-in fade-in zoom-in duration-200 max-h-[90vh] overflow-y-auto">
                        <h2 className="text-xl font-bold mb-4 text-slate-900 dark:text-white">Create Schedule</h2>
                        <form onSubmit={createSchedule}>
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Schedule Name</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary-500 outline-none transition-all"
                                    required
                                    placeholder="e.g., daily_etl_job"
                                />
                            </div>

                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Pipeline</label>
                                <select
                                    value={formData.pipeline_name}
                                    onChange={(e) => setFormData({ ...formData, pipeline_name: e.target.value })}
                                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary-500 outline-none transition-all"
                                    required
                                >
                                    <option value="">Select a pipeline...</option>
                                    {pipelines.registered.length > 0 && (
                                        <optgroup label={`Registered Pipelines (${pipelines.registered.length})`}>
                                            {pipelines.registered.map(p => (
                                                <option key={p} value={p}>{p}</option>
                                            ))}
                                        </optgroup>
                                    )}
                                    {pipelines.templates.length > 0 && (
                                        <optgroup label={`Templates (${pipelines.templates.length})`}>
                                            {pipelines.templates.map(p => (
                                                <option key={p} value={p}>{p}</option>
                                            ))}
                                        </optgroup>
                                    )}
                                    {pipelines.metadata.length > 0 && (
                                        <optgroup label={`Historical Pipelines (${pipelines.metadata.length})`}>
                                            {pipelines.metadata.map(p => (
                                                <option key={`meta-${p}`} value={p}>{p}</option>
                                            ))}
                                        </optgroup>
                                    )}
                                </select>
                                {pipelines.registered.length === 0 && pipelines.templates.length === 0 && pipelines.metadata.length === 0 && (
                                    <p className="text-xs text-amber-600 mt-1">
                                        No pipelines available. Run a pipeline first or register one using @register_pipeline.
                                    </p>
                                )}
                            </div>

                            <div className="grid grid-cols-2 gap-4 mb-4">
                                <div>
                                    <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Type</label>
                                    <select
                                        value={formData.schedule_type}
                                        onChange={(e) => setFormData({ ...formData, schedule_type: e.target.value })}
                                        className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary-500 outline-none transition-all"
                                    >
                                        <option value="daily">Daily</option>
                                        <option value="hourly">Hourly</option>
                                        <option value="interval">Interval</option>
                                        <option value="cron">Cron</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Timezone</label>
                                    <select
                                        value={formData.timezone}
                                        onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                                        className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary-500 outline-none transition-all"
                                    >
                                        <option value="UTC">UTC</option>
                                        <option value="America/New_York">New York (EST/EDT)</option>
                                        <option value="America/Los_Angeles">Los Angeles (PST/PDT)</option>
                                        <option value="Europe/London">London (GMT/BST)</option>
                                        <option value="Europe/Paris">Paris (CET/CEST)</option>
                                        <option value="Asia/Tokyo">Tokyo (JST)</option>
                                        <option value="Asia/Shanghai">Shanghai (CST)</option>
                                    </select>
                                </div>
                            </div>

                            {formData.schedule_type === 'daily' && (
                                <div className="grid grid-cols-2 gap-4 mb-4">
                                    <div>
                                        <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Hour (0-23)</label>
                                        <input
                                            type="number"
                                            min="0"
                                            max="23"
                                            value={formData.hour}
                                            onChange={(e) => setFormData({ ...formData, hour: parseInt(e.target.value) })}
                                            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary-500 outline-none transition-all"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Minute (0-59)</label>
                                        <input
                                            type="number"
                                            min="0"
                                            max="59"
                                            value={formData.minute}
                                            onChange={(e) => setFormData({ ...formData, minute: parseInt(e.target.value) })}
                                            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary-500 outline-none transition-all"
                                        />
                                    </div>
                                </div>
                            )}

                            {formData.schedule_type === 'hourly' && (
                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Minute (0-59)</label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="59"
                                        value={formData.minute}
                                        onChange={(e) => setFormData({ ...formData, minute: parseInt(e.target.value) })}
                                        className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary-500 outline-none transition-all"
                                    />
                                </div>
                            )}

                            {formData.schedule_type === 'interval' && (
                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Interval (seconds)</label>
                                    <input
                                        type="number"
                                        min="1"
                                        value={formData.interval_seconds}
                                        onChange={(e) => setFormData({ ...formData, interval_seconds: parseInt(e.target.value) })}
                                        className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary-500 outline-none transition-all"
                                    />
                                </div>
                            )}

                            {formData.schedule_type === 'cron' && (
                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Cron Expression</label>
                                    <input
                                        type="text"
                                        value={formData.cron_expression}
                                        onChange={(e) => setFormData({ ...formData, cron_expression: e.target.value })}
                                        className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary-500 outline-none transition-all font-mono"
                                        placeholder="* * * * *"
                                    />
                                    <p className="text-xs text-slate-500 mt-1">
                                        Format: minute hour day month day-of-week
                                    </p>
                                </div>
                            )}

                            <div className="flex justify-end gap-3 mt-6">
                                <Button
                                    variant="ghost"
                                    type="button"
                                    onClick={() => setShowCreateModal(false)}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    variant="primary"
                                >
                                    Create Schedule
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {showHistoryModal && selectedSchedule && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl w-full max-w-2xl border border-slate-200 dark:border-slate-700 shadow-2xl animate-in fade-in zoom-in duration-200 max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                    <History size={20} />
                                    Execution History
                                </h2>
                                <p className="text-slate-500 text-sm">{selectedSchedule.pipeline_name}</p>
                            </div>
                            <Button variant="ghost" onClick={() => setShowHistoryModal(false)}>
                                <XCircle size={20} />
                            </Button>
                        </div>

                        {historyLoading ? (
                            <div className="flex justify-center py-8">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
                            </div>
                        ) : history.length > 0 ? (
                            <div className="space-y-4">
                                {history.map((run, i) => (
                                    <div key={i} className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-100 dark:border-slate-700">
                                        <div className="flex items-center gap-4">
                                            <div className={`p-2 rounded-full ${run.success ? 'bg-emerald-100 text-emerald-600' : 'bg-rose-100 text-rose-600'}`}>
                                                {run.success ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
                                            </div>
                                            <div>
                                                <div className="font-medium text-slate-900 dark:text-white">
                                                    {format(new Date(run.started_at), 'MMM d, yyyy HH:mm:ss')}
                                                </div>
                                                <div className="text-xs text-slate-500">
                                                    Duration: {run.duration_seconds ? `${run.duration_seconds.toFixed(2)}s` : 'N/A'}
                                                </div>
                                            </div>
                                        </div>
                                        {!run.success && (
                                            <div className="text-sm text-rose-600 max-w-xs truncate" title={run.error}>
                                                {run.error}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-8 text-slate-500">
                                No execution history found.
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
