import React, { useEffect, useState } from 'react'
import { Routes, Route, Link, useParams } from 'react-router-dom'
import { LayoutDashboard, Activity, Database, Settings, Play, ArrowRight, Box, FileText, Layers, FlaskConical, BarChart2 } from 'lucide-react'
import { Layout } from './components/Layout'
import { Card, CardHeader, CardTitle, CardContent } from './components/ui/Card'
import { Badge } from './components/ui/Badge'
import { Button } from './components/ui/Button'
import { Dashboard } from './components/Dashboard'
import { Runs } from './components/Runs'
import { RunDetails } from './components/RunDetails'
import { Experiments } from './components/Experiments'
import { ExperimentDetails } from './components/ExperimentDetails'
import { format } from 'date-fns'

function App() {
    return (
        <Layout>
            <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/pipelines" element={<Pipelines />} />
                <Route path="/runs" element={<Runs />} />
                <Route path="/runs/:runId" element={<RunDetails />} />
                <Route path="/assets" element={<Assets />} />
                <Route path="/experiments" element={<Experiments />} />
                <Route path="/experiments/:experimentId" element={<ExperimentDetails />} />
                <Route path="/settings" element={<div className="p-8">Settings (Coming Soon)</div>} />
            </Routes>
        </Layout>
    )
}

function Pipelines() {
    const [pipelines, setPipelines] = useState([]);

    useEffect(() => {
        fetch('/api/pipelines')
            .then(res => res.json())
            .then(data => setPipelines(data.pipelines))
            .catch(err => console.error(err));
    }, []);

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Pipelines</h2>
                <p className="text-slate-500 mt-2">Manage and monitor your ML pipelines.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {pipelines.length > 0 ? (
                    pipelines.map((p, i) => (
                        <Card key={i} className="group cursor-pointer hover:border-primary-200">
                            <div className="flex items-start justify-between mb-4">
                                <div className="p-3 bg-primary-50 rounded-lg text-primary-600 group-hover:bg-primary-600 group-hover:text-white transition-colors">
                                    <Layers size={24} />
                                </div>
                                <Badge variant="success">Active</Badge>
                            </div>
                            <h3 className="text-lg font-bold text-slate-900 mb-2">{p}</h3>
                            <p className="text-sm text-slate-500 mb-4">Pipeline description placeholder.</p>
                            <div className="flex items-center justify-between pt-4 border-t border-slate-100">
                                <span className="text-xs text-slate-400">Last run: 2 hours ago</span>
                                <Button variant="ghost" size="sm" className="text-primary-600 hover:text-primary-700 p-0">
                                    View Details <ArrowRight size={16} className="ml-1" />
                                </Button>
                            </div>
                        </Card>
                    ))
                ) : (
                    <div className="col-span-full p-12 text-center bg-white rounded-xl border border-slate-100 border-dashed">
                        <div className="mx-auto w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center mb-4">
                            <Play className="text-slate-400" />
                        </div>
                        <h3 className="text-lg font-medium text-slate-900">No pipelines found</h3>
                        <p className="text-slate-500 mt-1">Run a pipeline locally to see it appear here.</p>
                    </div>
                )}
            </div>
        </div>
    )
}

function RecentRunsList({ limit }) {
    const [runs, setRuns] = useState([]);

    useEffect(() => {
        fetch(`/api/runs?limit=${limit || 20}`)
            .then(res => res.json())
            .then(data => setRuns(data.runs))
            .catch(err => console.error(err));
    }, [limit]);

    if (runs.length === 0) {
        return <div className="p-8 text-center text-slate-500">No runs found.</div>;
    }

    return (
        <table className="w-full text-left">
            <thead className="bg-slate-50 border-b border-slate-100">
                <tr>
                    <th className="px-6 py-4 font-semibold text-xs text-slate-500 uppercase tracking-wider">Run ID</th>
                    <th className="px-6 py-4 font-semibold text-xs text-slate-500 uppercase tracking-wider">Pipeline</th>
                    <th className="px-6 py-4 font-semibold text-xs text-slate-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-4 font-semibold text-xs text-slate-500 uppercase tracking-wider">Duration</th>
                    <th className="px-6 py-4 font-semibold text-xs text-slate-500 uppercase tracking-wider">Date</th>
                    <th className="px-6 py-4 font-semibold text-xs text-slate-500 uppercase tracking-wider"></th>
                </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
                {runs.map((run) => (
                    <tr key={run.run_id} className="hover:bg-slate-50/50 transition-colors group">
                        <td className="px-6 py-4">
                            <div className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${run.status === 'completed' ? 'bg-emerald-500' : 'bg-rose-500'}`}></div>
                                <span className="font-mono text-sm text-slate-700">{run.run_id.substring(0, 8)}</span>
                            </div>
                        </td>
                        <td className="px-6 py-4 text-slate-900 font-medium">{run.pipeline_name}</td>
                        <td className="px-6 py-4">
                            <Badge variant={run.status === 'completed' ? 'success' : run.status === 'failed' ? 'danger' : 'warning'}>
                                {run.status}
                            </Badge>
                        </td>
                        <td className="px-6 py-4 text-slate-500 font-mono text-sm">{run.duration ? `${run.duration.toFixed(2)}s` : '-'}</td>
                        <td className="px-6 py-4 text-slate-500 text-sm">
                            {run.start_time ? format(new Date(run.start_time), 'MMM d, HH:mm') : '-'}
                        </td>
                        <td className="px-6 py-4 text-right">
                            <Link to={`/runs/${run.run_id}`}>
                                <Button variant="ghost" size="sm" className="opacity-0 group-hover:opacity-100 transition-opacity">
                                    Details
                                </Button>
                            </Link>
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    )
}

function Assets() {
    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Artifacts</h2>
                <p className="text-slate-500 mt-2">Browse all generated assets and artifacts.</p>
            </div>
            <RecentAssetsList />
        </div>
    )
}

function RecentAssetsList({ limit }) {
    const [assets, setAssets] = useState([]);

    useEffect(() => {
        fetch(`/api/assets?limit=${limit || 50}`)
            .then(res => res.json())
            .then(data => setAssets(data.assets))
            .catch(err => console.error(err));
    }, [limit]);

    if (assets.length === 0) {
        return (
            <div className="p-12 text-center bg-white rounded-xl border border-slate-100 border-dashed">
                <div className="mx-auto w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center mb-4">
                    <Database className="text-slate-400" />
                </div>
                <h3 className="text-lg font-medium text-slate-900">No artifacts found</h3>
                <p className="text-slate-500 mt-1">Artifacts generated by pipelines will appear here.</p>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {assets.map((asset) => (
                <Card key={asset.artifact_id} className="group hover:border-primary-200 transition-all">
                    <div className="flex items-start justify-between mb-4">
                        <div className="p-2 bg-slate-100 rounded-lg text-slate-600 group-hover:bg-primary-50 group-hover:text-primary-600 transition-colors">
                            {asset.type === 'dataset' ? <Database size={20} /> :
                                asset.type === 'model' ? <Box size={20} /> :
                                    <FileText size={20} />}
                        </div>
                        <span className="text-xs font-mono text-slate-400">{asset.artifact_id.substring(0, 8)}</span>
                    </div>

                    <h3 className="font-bold text-slate-900 mb-1 truncate" title={asset.name}>
                        {asset.name || 'Unnamed Asset'}
                    </h3>
                    <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold mb-4">{asset.type}</p>

                    <div className="flex items-center justify-between pt-4 border-t border-slate-100 text-sm text-slate-500">
                        <span>{new Date(asset.created_at).toLocaleDateString()}</span>
                        <span className="font-mono text-xs bg-slate-100 px-2 py-1 rounded">v1</span>
                    </div>
                </Card>
            ))}
        </div>
    )
}

export default App

