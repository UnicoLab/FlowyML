import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, PlayCircle, FolderKanban, FlaskConical, Database, Settings, Trophy, Calendar, MessageSquare, Moon, Sun, Key, Package } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { ProjectSelector } from './ui/ProjectSelector';

function NavLink({ to, icon, label }) {
    const location = useLocation();
    const isActive = location.pathname === to;

    return (
        <Link
            to={to}
            className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200 group ${isActive
                ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400 font-medium shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-white'
                }`}
        >
            <span className={`transition-colors ${isActive ? 'text-primary-600 dark:text-primary-400' : 'text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300'
                }`}>
                {icon}
            </span>
            <span className="text-sm">{label}</span>
        </Link>
    );
}

export function Layout({ children }) {
    const { theme, toggleTheme } = useTheme();

    const navLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
        { icon: FolderKanban, label: 'Projects', path: '/projects' },
        { icon: PlayCircle, label: 'Pipelines', path: '/pipelines' },
        { icon: Calendar, label: 'Schedules', path: '/schedules' },
        { icon: PlayCircle, label: 'Runs', path: '/runs' },
        { icon: Trophy, label: 'Leaderboard', path: '/leaderboard' },
        { icon: Database, label: 'Assets', path: '/assets' },
        { icon: FlaskConical, label: 'Experiments', path: '/experiments' },
        { icon: MessageSquare, label: 'Traces', path: '/traces' },
    ];

    return (
        <div className="flex h-screen bg-slate-50 dark:bg-slate-900">
            {/* Sidebar */}
            <aside className="w-64 bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 flex flex-col shadow-sm z-10">
                <div className="p-6 border-b border-slate-100 dark:border-slate-700 flex items-center gap-3">
                    <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center shadow-lg shadow-primary-500/30">
                        <PlayCircle className="text-white w-5 h-5" />
                    </div>
                    <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">flowyml</h1>
                </div>

                <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
                    <div className="px-4 py-2 text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                        Platform
                    </div>
                    {navLinks.map((link) => (
                        <NavLink
                            key={link.path}
                            to={link.path}
                            icon={<link.icon size={18} />}
                            label={link.label}
                        />
                    ))}
                    <div className="px-4 py-2 text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mt-4">
                        Settings
                    </div>
                    <NavLink to="/plugins" icon={<Package size={18} />} label="Plugins" />
                    <NavLink to="/tokens" icon={<Key size={18} />} label="API Tokens" />
                    <NavLink to="/settings" icon={<Settings size={18} />} label="Settings" />
                </nav>

                <div className="p-4 border-t border-slate-100 dark:border-slate-700">
                    <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-4 border border-slate-100 dark:border-slate-700">
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">flowyml v0.1.0</p>
                        <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">Local Environment</p>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 flex flex-col overflow-hidden">
                {/* Header with Project Selector */}
                <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4 flex items-center justify-between shadow-sm">
                    <ProjectSelector />

                    <button
                        onClick={toggleTheme}
                        className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                        aria-label="Toggle theme"
                    >
                        {theme === 'dark' ? (
                            <Sun size={20} className="text-slate-400" />
                        ) : (
                            <Moon size={20} className="text-slate-400" />
                        )}
                    </button>
                </header>

                {/* Page Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {children}
                </div>
            </main>
        </div>
    );
}
