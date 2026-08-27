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
    Key,
    Package,
    ChevronLeft,
    ChevronRight,
    Activity,
    Rocket,
    Microscope,
    ClipboardCheck,
    X
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Bumped by semantic-release via [tool.semantic_release].version_variables,
// which rewrites assignments only. The entry used to point at the version
// printed inline in the JSX below, which it cannot match, so every release
// silently left the sidebar showing the previous version.
const VERSION = "2.2.0";

const NAV_GROUPS = [
    {
        title: 'Workspace',
        items: [
            { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
            { icon: FolderKanban, label: 'Projects', path: '/projects' },
        ],
    },
    {
        title: 'Automation',
        items: [
            { icon: PlayCircle, label: 'Pipelines', path: '/pipelines' },
            { icon: Calendar, label: 'Schedules', path: '/schedules' },
            { icon: PlayCircle, label: 'Runs', path: '/runs' },
            { icon: Rocket, label: 'Deployments', path: '/deployments' },
        ],
    },
    {
        title: 'Insights',
        items: [
            { icon: Trophy, label: 'Leaderboard', path: '/leaderboard' },
            { icon: FlaskConical, label: 'Experiments', path: '/experiments' },
            { icon: ClipboardCheck, label: 'Evaluations', path: '/evaluations' },
            { icon: Microscope, label: 'Model Explorer', path: '/model-explorer' },
        ],
    },
    {
        title: 'Data & Observability',
        items: [
            { icon: Database, label: 'Assets', path: '/assets' },
            { icon: Activity, label: 'GenAI Traces', path: '/traces' },
            { icon: Activity, label: 'Observability', path: '/observability' },
        ],
    },
];

const SETTINGS_LINKS = [
    { icon: Package, label: 'Plugins', path: '/plugins' },
    { icon: Key, label: 'API Tokens', path: '/tokens' },
    { icon: Settings, label: 'Settings', path: '/settings' },
];

export function Sidebar({ collapsed, setCollapsed, isMobile = false, mobileOpen = false, onMobileClose }) {
    const location = useLocation();
    const [logoError, setLogoError] = useState(false);

    // On mobile, sidebar is a fixed overlay drawer
    const sidebarClasses = isMobile
        ? `fixed top-0 left-0 h-screen w-72 bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 flex flex-col shadow-2xl z-40 transform transition-transform duration-250 ease-out ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`
        : 'h-screen bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 flex flex-col shadow-sm z-20 relative';

    // On mobile, always show full (not collapsed)
    const isCollapsed = isMobile ? false : collapsed;
    const sidebarWidth = isMobile ? undefined : (isCollapsed ? 80 : 256);

    const handleNavClick = () => {
        // Close sidebar on mobile after navigation
        if (isMobile && onMobileClose) {
            onMobileClose();
        }
    };

    const content = (
        <>
            {/* Logo Section */}
            <div className="p-4 border-b border-slate-100 dark:border-slate-700 flex items-center gap-3 h-[73px] shrink-0">
                {logoError ? (
                    <div className="w-12 h-12 min-w-[48px] rounded-lg shadow-lg bg-gradient-to-br from-primary-500 to-indigo-600 flex items-center justify-center text-white font-bold text-xl select-none">
                        F
                    </div>
                ) : (
                    <img
                        src="/logo.png"
                        alt="FlowyML"
                        className="w-12 h-12 min-w-[48px] rounded-lg shadow-lg object-cover object-top bg-white dark:bg-slate-800"
                        onError={() => setLogoError(true)}
                    />
                )}
                <AnimatePresence>
                    {!isCollapsed && (
                        <motion.div
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -10 }}
                            className="flex flex-col min-w-0"
                        >
                            <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight whitespace-nowrap overflow-hidden">
                                FlowyML
                            </h1>
                            <span className="text-[10px] text-slate-400 dark:text-slate-500">by UnicoLab</span>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Mobile close button */}
                {isMobile && (
                    <button
                        onClick={onMobileClose}
                        className="ml-auto p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 transition-colors"
                        aria-label="Close sidebar"
                    >
                        <X size={20} />
                    </button>
                )}
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-3 md:p-4 space-y-3 overflow-y-auto overflow-x-hidden scrollbar-thin">
                {NAV_GROUPS.map((group) => (
                    <div key={group.title} className="space-y-0.5">
                        <div className={`px-4 py-1 text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider transition-opacity duration-200 ${isCollapsed ? 'opacity-0 h-0 py-0' : 'opacity-100'}`}>
                            {group.title}
                        </div>
                        {group.items.map((link) => (
                            <NavItem
                                key={link.path}
                                to={link.path}
                                icon={link.icon}
                                label={link.label}
                                collapsed={isCollapsed}
                                isActive={location.pathname === link.path}
                                onClick={handleNavClick}
                            />
                        ))}
                    </div>
                ))}

                <div className={`px-4 py-2 text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mt-2 transition-opacity duration-200 ${isCollapsed ? 'opacity-0 h-0 py-0' : 'opacity-100'}`}>
                    Settings
                </div>
                {SETTINGS_LINKS.map((link) => (
                    <NavItem
                        key={link.path}
                        to={link.path}
                        icon={link.icon}
                        label={link.label}
                        collapsed={isCollapsed}
                        isActive={location.pathname === link.path}
                        onClick={handleNavClick}
                    />
                ))}
            </nav>

            {/* Footer */}
            <div className="p-3 md:p-4 border-t border-slate-100 dark:border-slate-700 shrink-0">
                <div className={`bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 rounded-lg p-3 border border-slate-200 dark:border-slate-700 transition-all duration-200 ${isCollapsed ? 'p-2 flex justify-center' : ''}`}>
                    {!isCollapsed ? (
                        <>
                            <div className="flex items-center gap-2 mb-2">
                                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                <p className="text-xs font-semibold text-slate-600 dark:text-slate-300 whitespace-nowrap">FlowyML v{VERSION}</p>
                            </div>
                            <p className="text-[10px] text-slate-400 dark:text-slate-500 whitespace-nowrap">
                                Made with ❤️ by <span className="font-medium text-primary-500">UnicoLab</span>
                            </p>
                        </>
                    ) : (
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" title="Online" />
                    )}
                </div>
            </div>

            {/* Collapse Toggle (desktop only) */}
            {!isMobile && (
                <button
                    onClick={() => setCollapsed(!collapsed)}
                    className="absolute -right-3 top-20 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-full p-1 shadow-md text-slate-500 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
                >
                    {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
                </button>
            )}
        </>
    );

    // On mobile, render without framer-motion width animation (CSS transition handles it)
    if (isMobile) {
        return (
            <aside className={sidebarClasses}>
                {content}
            </aside>
        );
    }

    // Desktop: animated width with framer-motion
    return (
        <motion.aside
            initial={false}
            animate={{ width: sidebarWidth }}
            className={sidebarClasses}
        >
            {content}
        </motion.aside>
    );
}

function NavItem({ to, icon: Icon, label, collapsed, isActive, onClick }) {
    return (
        <NavLink
            to={to}
            onClick={onClick}
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
