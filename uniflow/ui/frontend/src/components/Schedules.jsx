import React, { useState, useEffect } from 'react';
import { Calendar, Play, Pause, Trash2, Plus, Clock } from 'lucide-react';
import { format } from 'date-fns';

export default function Schedules() {
    const [schedules, setSchedules] = useState([]);
    const [pipelines, setPipelines] = useState({ registered: [], templates: [] });
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);

    // Form state
    const [formData, setFormData] = useState({
        name: '',
        pipeline_name: '',
        schedule_type: 'daily',
        hour: 0,
        minute: 0,
        interval_seconds: 3600
    });

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [schedulesRes, pipelinesRes] = await Promise.all([
                fetch('/api/schedules/'),
                fetch('/api/schedules/registered-pipelines')
            ]);

            const schedulesData = await schedulesRes.json();
            const pipelinesData = await pipelinesRes.json();

            setSchedules(schedulesData);
            setPipelines(pipelinesData);
        } catch (error) {
            console.error('Failed to fetch data:', error);
        } finally {
            setLoading(false);
        }
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
                    interval_seconds: 3600
                });
                fetchData();
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

    return (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold">📅 Schedules</h1>
                <button
                    onClick={() => setShowCreateModal(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                >
                    <Plus className="w-4 h-4" />
                    New Schedule
                </button>
            </div>

            {showCreateModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-gray-800 p-6 rounded-lg w-full max-w-md border border-gray-700">
                        <h2 className="text-xl font-bold mb-4">Create Schedule</h2>
                        <form onSubmit={createSchedule}>
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-1">Schedule Name</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none"
                                    required
                                />
                            </div>

                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-1">Pipeline</label>
                                <select
                                    value={formData.pipeline_name}
                                    onChange={(e) => setFormData({ ...formData, pipeline_name: e.target.value })}
                                    className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none"
                                    required
                                >
                                    <option value="">Select a pipeline...</option>
                                    <optgroup label="Registered Pipelines">
                                        {pipelines.registered.map(p => (
                                            <option key={p} value={p}>{p}</option>
                                        ))}
                                    </optgroup>
                                    <optgroup label="Templates">
                                        {pipelines.templates.map(p => (
                                            <option key={p} value={p}>{p}</option>
                                        ))}
                                    </optgroup>
                                </select>
                            </div>

                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-1">Type</label>
                                <select
                                    value={formData.schedule_type}
                                    onChange={(e) => setFormData({ ...formData, schedule_type: e.target.value })}
                                    className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none"
                                >
                                    <option value="daily">Daily</option>
                                    <option value="hourly">Hourly</option>
                                    <option value="interval">Interval</option>
                                </select>
                            </div>

                            {formData.schedule_type === 'daily' && (
                                <div className="grid grid-cols-2 gap-4 mb-4">
                                    <div>
                                        <label className="block text-sm font-medium mb-1">Hour (0-23)</label>
                                        <input
                                            type="number"
                                            min="0"
                                            max="23"
                                            value={formData.hour}
                                            onChange={(e) => setFormData({ ...formData, hour: parseInt(e.target.value) })}
                                            className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-1">Minute (0-59)</label>
                                        <input
                                            type="number"
                                            min="0"
                                            max="59"
                                            value={formData.minute}
                                            onChange={(e) => setFormData({ ...formData, minute: parseInt(e.target.value) })}
                                            className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none"
                                        />
                                    </div>
                                </div>
                            )}

                            {formData.schedule_type === 'hourly' && (
                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-1">Minute (0-59)</label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="59"
                                        value={formData.minute}
                                        onChange={(e) => setFormData({ ...formData, minute: parseInt(e.target.value) })}
                                        className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none"
                                    />
                                </div>
                            )}

                            {formData.schedule_type === 'interval' && (
                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-1">Interval (seconds)</label>
                                    <input
                                        type="number"
                                        min="1"
                                        value={formData.interval_seconds}
                                        onChange={(e) => setFormData({ ...formData, interval_seconds: parseInt(e.target.value) })}
                                        className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none"
                                    />
                                </div>
                            )}

                            <div className="flex justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={() => setShowCreateModal(false)}
                                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded"
                                >
                                    Create Schedule
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {loading ? (
                <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                </div>
            ) : schedules.length === 0 ? (
                <div className="text-center py-12 bg-gray-800/30 rounded-lg border-2 border-dashed border-gray-700">
                    <Calendar className="w-12 h-12 mx-auto text-gray-600 mb-4" />
                    <p className="text-gray-400">No active schedules</p>
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="mt-4 text-blue-400 hover:text-blue-300"
                    >
                        Create your first schedule
                    </button>
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-4">
                    {schedules.map((schedule) => (
                        <div key={schedule.pipeline_name} className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-4 flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <div className={`p-2 rounded-lg ${schedule.enabled ? 'bg-green-500/10' : 'bg-gray-700'}`}>
                                    <Clock className={`w-6 h-6 ${schedule.enabled ? 'text-green-400' : 'text-gray-400'}`} />
                                </div>
                                <div>
                                    <h3 className="font-bold">{schedule.pipeline_name}</h3>
                                    <div className="flex items-center gap-4 text-sm text-gray-400">
                                        <span className="capitalize">{schedule.schedule_type}</span>
                                        <span>•</span>
                                        <span>Next: {schedule.next_run ? format(new Date(schedule.next_run), 'MMM d, HH:mm:ss') : 'N/A'}</span>
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => toggleSchedule(schedule.pipeline_name, schedule.enabled)}
                                    className={`p-2 rounded hover:bg-gray-700 transition-colors ${schedule.enabled ? 'text-green-400' : 'text-yellow-400'}`}
                                    title={schedule.enabled ? 'Pause' : 'Resume'}
                                >
                                    {schedule.enabled ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                                </button>
                                <button
                                    onClick={() => deleteSchedule(schedule.pipeline_name)}
                                    className="p-2 rounded hover:bg-gray-700 text-gray-500 hover:text-red-400 transition-colors"
                                    title="Delete"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
