import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { CheckCircle, XCircle, Clock, Calendar, Package, ArrowRight, BarChart2, FileText, Database, Box } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { format } from 'date-fns';

export function RunDetails() {
    const { runId } = useParams();
    const [run, setRun] = useState(null);
    const [artifacts, setArtifacts] = useState([]);
    const [metrics, setMetrics] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [runRes, assetsRes, metricsRes] = await Promise.all([
                    fetch(`/api/runs/${runId}`),
                    fetch(`/api/assets?run_id=${runId}`),
                    fetch(`/api/runs/${runId}/metrics`) // Assuming this endpoint exists or we use assets
                ]);

                const runData = await runRes.json();
                const assetsData = await assetsRes.json();

                // Metrics might be fetched differently, but for now let's assume we get them from assets (Metrics asset) 
                // or we can fetch them from the metrics endpoint if implemented.
                // The current metrics endpoint returns list of metrics.
                let metricsData = [];
                try {
                    const mRes = await fetch(`/api/runs/${runId}/metrics`);
                    if (mRes.ok) {
                        const mJson = await mRes.json();
                        metricsData = mJson.metrics || [];
                    }
                } catch (e) {
                    console.warn("Failed to fetch metrics", e);
                }

                setRun(runData);
                setArtifacts(assetsData.assets || []);
                setMetrics(metricsData);
                setLoading(false);
            } catch (err) {
                console.error(err);
                setLoading(false);
            }
        };

        fetchData();
    }, [runId]);

    if (loading) return <div className="p-8 text-center">Loading run details...</div>;
    if (!run) return <div className="p-8 text-center">Run not found</div>;

    const statusVariant =
        run.status === 'completed' ? 'success' :
            run.status === 'failed' ? 'danger' : 'warning';

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <Link to="/runs" className="text-sm text-slate-500 hover:text-slate-700">Runs</Link>
                        <span className="text-slate-300">/</span>
                        <span className="text-sm text-slate-900 font-medium">{run.run_id}</span>
                    </div>
                    <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-3">
                        Run: <span className="font-mono text-slate-500">{run.run_id.substring(0, 8)}</span>
                    </h2>
                    <p className="text-slate-500 mt-1">Pipeline: <span className="font-medium text-slate-700">{run.pipeline_name}</span></p>
                </div>
                <Badge variant={statusVariant} className="text-sm px-3 py-1 uppercase tracking-wide">
                    {run.status}
                </Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card>
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-50 rounded-lg text-blue-600">
                            <Clock size={24} />
                        </div>
                        <div>
                            <p className="text-sm text-slate-500 font-medium">Duration</p>
                            <p className="text-xl font-bold text-slate-900">{run.duration ? `${run.duration.toFixed(2)}s` : '-'}</p>
                        </div>
                    </div>
                </Card>

                <Card>
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-purple-50 rounded-lg text-purple-600">
                            <Calendar size={24} />
                        </div>
                        <div>
                            <p className="text-sm text-slate-500 font-medium">Started At</p>
                            <p className="text-xl font-bold text-slate-900">
                                {run.start_time ? format(new Date(run.start_time), 'MMM d, HH:mm:ss') : '-'}
                            </p>
                        </div>
                    </div>
                </Card>

                <Card>
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-emerald-50 rounded-lg text-emerald-600">
                            <Package size={24} />
                        </div>
                        <div>
                            <p className="text-sm text-slate-500 font-medium">Steps Completed</p>
                            <p className="text-xl font-bold text-slate-900">
                                {run.steps ? Object.values(run.steps).filter(s => s.success).length : 0} / {run.steps ? Object.keys(run.steps).length : 0}
                            </p>
                        </div>
                    </div>
                </Card>
            </div>

            <h3 className="text-xl font-bold text-slate-900 mt-8 mb-4">Execution Steps</h3>
            <div className="space-y-4">
                {run.steps && Object.entries(run.steps).map(([stepName, stepData]) => (
                    <StepCard
                        key={stepName}
                        name={stepName}
                        data={stepData}
                        artifacts={artifacts.filter(a => a.step === stepName)}
                        metrics={metrics.filter(m => m.step === stepName || m.name.startsWith(stepName))} // Simple filtering
                    />
                ))}
            </div>
        </div>
    );
}

function StepCard({ name, data, artifacts, metrics }) {
    return (
        <Card className="border-l-4 border-l-primary-500 overflow-hidden">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    {data.success ? (
                        <CheckCircle className="text-emerald-500" size={20} />
                    ) : (
                        <XCircle className="text-rose-500" size={20} />
                    )}
                    <h4 className="text-lg font-semibold text-slate-900">{name}</h4>
                </div>
                <div className="flex items-center gap-3">
                    {data.cached && (
                        <Badge variant="default" className="bg-slate-100 text-slate-600">Cached</Badge>
                    )}
                    <span className="text-sm text-slate-500 font-mono">{data.duration.toFixed(2)}s</span>
                </div>
            </div>

            {data.error && (
                <div className="mt-4 p-4 bg-rose-50 border border-rose-100 rounded-lg text-rose-700 text-sm font-mono whitespace-pre-wrap">
                    {data.error}
                </div>
            )}

            {/* Artifacts Section */}
            {artifacts && artifacts.length > 0 && (
                <div className="mt-4 pt-4 border-t border-slate-100">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                        <Package size={14} /> Artifacts
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {artifacts.map(art => (
                            <div key={art.artifact_id} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg border border-slate-100">
                                <div className="p-2 bg-white rounded-md text-slate-500 shadow-sm">
                                    {art.type === 'Dataset' ? <Database size={16} /> :
                                        art.type === 'Model' ? <Box size={16} /> :
                                            <FileText size={16} />}
                                </div>
                                <div className="min-w-0">
                                    <p className="text-sm font-medium text-slate-900 truncate" title={art.name}>{art.name}</p>
                                    <p className="text-xs text-slate-500 truncate">{art.type}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Metrics Section (if any specific to step) */}
            {/* Note: Metrics might be associated with run, not always step explicitly in current DB schema unless step field is used */}
        </Card>
    );
}
