import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import { Sun, Moon, ChevronRight, Home, Server, ExternalLink, Menu, LogOut, User } from 'lucide-react';
import { useTheme } from '../../contexts/ThemeContext';
import { ProjectSelector } from '../ui/ProjectSelector';
import { useConfig } from '../../utils/api';
import { useAuth } from '../../contexts/AuthContext';

export function Header({ isMobile = false, onMenuClick }) {
    const { theme, toggleTheme } = useTheme();
    const location = useLocation();
    const { config, loading } = useConfig();
    const { user, logout } = useAuth();

    // Generate breadcrumbs from path
    const pathnames = location.pathname.split('/').filter((x) => x);
    const isRemoteStack = !loading && config?.execution_mode === 'remote';
    const remoteServices = isRemoteStack && Array.isArray(config?.remote_services)
        ? config.remote_services
        : [];

    return (
        <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-3 md:px-6 py-3 md:py-4 flex items-center justify-between shadow-sm z-10 gap-2 min-h-[57px]">
            <div className="flex items-center gap-2 md:gap-4 flex-1 min-w-0">
                {/* Mobile hamburger menu */}
                {isMobile && (
                    <button
                        onClick={onMenuClick}
                        className="p-2 -ml-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-slate-600 dark:text-slate-400 shrink-0"
                        aria-label="Toggle sidebar"
                    >
                        <Menu size={22} />
                    </button>
                )}

                {/* Breadcrumbs */}
                <nav className="flex items-center text-sm text-slate-500 dark:text-slate-400 min-w-0 overflow-hidden">
                    <Link to="/" className="hover:text-primary-600 dark:hover:text-primary-400 transition-colors shrink-0">
                        <Home size={16} />
                    </Link>
                    {pathnames.length > 0 && (
                        <ChevronRight size={14} className="mx-1 md:mx-2 text-slate-300 dark:text-slate-600 shrink-0" />
                    )}
                    {pathnames.map((name, index) => {
                        const routeTo = `/${pathnames.slice(0, index + 1).join('/')}`;
                        const isLast = index === pathnames.length - 1;
                        const formattedName = name.charAt(0).toUpperCase() + name.slice(1).replace(/-/g, ' ');

                        // On mobile, show only the last breadcrumb
                        if (isMobile && !isLast) return null;

                        return (
                            <React.Fragment key={name}>
                                {isLast ? (
                                    <span className="font-medium text-slate-900 dark:text-white truncate">
                                        {formattedName}
                                    </span>
                                ) : (
                                    <Link
                                        to={routeTo}
                                        className="hover:text-primary-600 dark:hover:text-primary-400 transition-colors truncate"
                                    >
                                        {formattedName}
                                    </Link>
                                )}
                                {!isLast && (
                                    <ChevronRight size={14} className="mx-1 md:mx-2 text-slate-300 dark:text-slate-600 shrink-0" />
                                )}
                            </React.Fragment>
                        );
                    })}
                </nav>
            </div>

            <div className="flex items-center gap-2 md:gap-4 shrink-0">
                {/* Remote stack indicator — hidden on mobile, compact on tablet */}
                {isRemoteStack && !isMobile && (
                    <div className="hidden lg:flex flex-col gap-2 px-4 py-2 rounded-xl bg-primary-50 text-primary-800 border border-primary-100 dark:bg-primary-900/20 dark:text-primary-200 dark:border-primary-900/40">
                        <div className="flex items-center gap-2 text-xs uppercase tracking-wide font-semibold">
                            <Server size={14} /> Remote Stack
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            {config?.remote_ui_url && (
                                <a
                                    href={config.remote_ui_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1 text-xs font-medium bg-white/70 dark:bg-slate-800/40 px-2 py-1 rounded-lg hover:underline"
                                >
                                    UI <ExternalLink size={12} />
                                </a>
                            )}
                            {config?.remote_server_url && (
                                <a
                                    href={config.remote_server_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1 text-xs font-medium bg-white/70 dark:bg-slate-800/40 px-2 py-1 rounded-lg hover:underline"
                                >
                                    API <ExternalLink size={12} />
                                </a>
                            )}
                            {remoteServices.map((service, idx) => (
                                <a
                                    key={`${service?.name || service?.label || 'service'}-${idx}`}
                                    href={service?.url || service?.link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1 text-xs font-medium bg-white/70 dark:bg-slate-800/40 px-2 py-1 rounded-lg hover:underline"
                                >
                                    {service?.label || service?.name || 'Service'} <ExternalLink size={12} />
                                </a>
                            ))}
                        </div>
                    </div>
                )}

                {/* Remote stack compact indicator on tablet */}
                {isRemoteStack && !isMobile && (
                    <div className="flex lg:hidden items-center gap-1 px-2 py-1.5 rounded-lg bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 text-xs font-semibold">
                        <Server size={14} />
                        <span className="hidden sm:inline">Remote</span>
                    </div>
                )}

                <div className="hidden md:block">
                    <ProjectSelector />
                </div>

                <div className="h-6 w-px bg-slate-200 dark:bg-slate-700 hidden md:block" />

                <button
                    onClick={toggleTheme}
                    className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-slate-500 hover:text-primary-600 dark:text-slate-400 dark:hover:text-primary-400"
                    aria-label="Toggle theme"
                >
                    {theme === 'dark' ? (
                        <Sun size={20} />
                    ) : (
                        <Moon size={20} />
                    )}
                </button>

                {user && (
                    <>
                        <div className="h-6 w-px bg-slate-200 dark:bg-slate-700 hidden sm:block" />
                        <div className="flex items-center gap-1 md:gap-2">
                            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-700/50 text-slate-700 dark:text-slate-300">
                                <User size={16} />
                                <span className="text-xs font-medium">{user.username}</span>
                            </div>
                            <button
                                onClick={logout}
                                className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-slate-500 hover:text-red-600 dark:text-slate-400 dark:hover:text-red-400 transition-colors"
                                title="Logout"
                            >
                                <LogOut size={18} />
                            </button>
                        </div>
                    </>
                )}
            </div>
        </header>
    );
}
