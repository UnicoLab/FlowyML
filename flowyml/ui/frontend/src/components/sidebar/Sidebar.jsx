import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
    LayoutDashboard,
    PlayCircle,
    FolderKanban,
    FlaskConical,
    Database,
    Settings,
    Trophy,
    Calendar,
    MessageSquare,
    Key,
    Package,
    ChevronLeft,
    ChevronRight,
    Menu
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const NAV_LINKS = [
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

const SETTINGS_LINKS = [
    { icon: Package, label: 'Plugins', path: '/plugins' },
    { icon: Key, label: 'API Tokens', path: '/tokens' },
    { icon: Settings, label: 'Settings', path: '/settings' },
];

export function Sidebar({ collapsed, setCollapsed }) {
    const location = useLocation();

    return (
        <motion.aside
            initial={false}
            animate={{ width: collapsed ? 80 : 256 }}
            className="h-screen bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 flex flex-col shadow-sm z-20 relative"
        >
            {/* Logo Section */}
            <div className="p-6 border-b border-slate-100 dark:border-slate-700 flex items-center gap-3 h-[73px]">
                <div className="w-8 h-8 min-w-[32px] bg-primary-600 rounded-lg flex items-center justify-center shadow-lg shadow-primary-500/30">
                    <PlayCircle className="text-white w-5 h-5" />
                </div>
                <AnimatePresence>
                    {!collapsed && (
                        <motion.h1
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -10 }}
                            className="text-xl font-bold text-slate-900 dark:text-white tracking-tight whitespace-nowrap overflow-hidden"
                        >
                            flowyml
                        </motion.h1>
                    )}
                </AnimatePresence>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-4 space-y-1 overflow-y-auto overflow-x-hidden scrollbar-thin scrollbar-thumb-slate-200 dark:scrollbar-thumb-slate-700">
                <div className={`px-4 py-2 text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider transition-opacity duration-200 ${collapsed ? 'opacity-0 h-0' : 'opacity-100'}`}>
                    Platform
                </div>
                {NAV_LINKS.map((link) => (
                    <NavItem
                        key={link.path}
                        to={link.path}
                        icon={link.icon}
                        label={link.label}
                        collapsed={collapsed}
                        isActive={location.pathname === link.path}
                    />
                ))}

                <div className={`px-4 py-2 text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mt-4 transition-opacity duration-200 ${collapsed ? 'opacity-0 h-0' : 'opacity-100'}`}>
                    Settings
                </div>
                {SETTINGS_LINKS.map((link) => (
                    <NavItem
                        key={link.path}
                        to={link.path}
                        icon={link.icon}
                        label={link.label}
                        collapsed={collapsed}
                        isActive={location.pathname === link.path}
                    />
                ))}
            </nav>

            {/* Footer */}
            <div className="p-4 border-t border-slate-100 dark:border-slate-700">
                <div className={`bg-slate-50 dark:bg-slate-900 rounded-lg p-4 border border-slate-100 dark:border-slate-700 transition-all duration-200 ${collapsed ? 'p-2 flex justify-center' : ''}`}>
                    {!collapsed ? (
                        <>
                            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 whitespace-nowrap">flowyml v0.1.0</p>
                            <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 whitespace-nowrap">Local Environment</p>
                        </>
                    ) : (
                        <div className="w-2 h-2 rounded-full bg-emerald-500" title="Online" />
                    )}
                </div>
            </div>

            {/* Collapse Toggle */}
            <button
                onClick={() => setCollapsed(!collapsed)}
                className="absolute -right-3 top-20 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-full p-1 shadow-md text-slate-500 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
            >
                {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            </button>
        </motion.aside>
    );
}

function NavItem({ to, icon: Icon, label, collapsed, isActive }) {
    return (
        <NavLink
            to={to}
            className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200 group relative ${isActive
                ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400 font-medium shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-white'
                }`}
            title={collapsed ? label : undefined}
        >
            <span className={`transition-colors flex-shrink-0 ${isActive ? 'text-primary-600 dark:text-primary-400' : 'text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300'
                }`}>
                <Icon size={20} />
            </span>
            {!collapsed && (
                <span className="text-sm whitespace-nowrap overflow-hidden text-ellipsis">{label}</span>
            )}
            {collapsed && isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary-600 rounded-r-full" />
            )}
        </NavLink>
    );
}
