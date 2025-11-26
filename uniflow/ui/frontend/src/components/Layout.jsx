import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Activity, Database, Settings, Play, Box, FlaskConical, MessageSquare } from 'lucide-react';
import { cn } from '../utils/cn';

export function Layout({ children }) {
    return (
        <div className="flex h-screen w-full bg-slate-50/50">
            <Sidebar />
            <main className="flex-1 overflow-auto">
                <div className="container mx-auto max-w-7xl p-8">
                    {children}
                </div>
            </main>
        </div>
    );
}

function Sidebar() {
    return (
        <aside className="w-64 bg-white border-r border-slate-200 flex flex-col shadow-sm z-10">
            <div className="p-6 border-b border-slate-100 flex items-center gap-3">
                <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center shadow-lg shadow-primary-500/30">
                    <Box className="text-white w-5 h-5" />
                </div>
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">Flowy</h1>
            </div>

            <nav className="flex-1 p-4 space-y-1">
                <div className="px-4 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Platform
                </div>
                <NavLink to="/" icon={<LayoutDashboard size={18} />} label="Dashboard" />
                <NavLink to="/pipelines" icon={<Play size={18} />} label="Pipelines" />
                <NavLink to="/runs" icon={<Activity size={18} />} label="Runs" />
                <NavLink to="/assets" icon={<Database size={18} />} label="Artifacts" />
                <NavLink to="/experiments" icon={<FlaskConical size={18} />} label="Experiments" />
                <NavLink to="/traces" icon={<MessageSquare size={18} />} label="Traces" />

                <div className="px-4 py-2 mt-6 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    System
                </div>
                <NavLink to="/settings" icon={<Settings size={18} />} label="Settings" />
            </nav>

            <div className="p-4 border-t border-slate-100">
                <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
                    <p className="text-xs font-medium text-slate-500">Flowy v0.1.0</p>
                    <p className="text-xs text-slate-400 mt-1">Local Environment</p>
                </div>
            </div>
        </aside>
    );
}

function NavLink({ to, icon, label }) {
    const location = useLocation();
    const isActive = location.pathname === to || (to !== '/' && location.pathname.startsWith(to));

    return (
        <Link
            to={to}
            className={cn(
                "flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200 group",
                isActive
                    ? "bg-primary-50 text-primary-700 font-medium shadow-sm"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
            )}
        >
            <span className={cn(
                "transition-colors",
                isActive ? "text-primary-600" : "text-slate-400 group-hover:text-slate-600"
            )}>
                {icon}
            </span>
            <span>{label}</span>
        </Link>
    );
}
