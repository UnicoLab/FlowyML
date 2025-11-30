import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import { Sun, Moon, ChevronRight, Home, Server, ExternalLink } from 'lucide-react';
import { useTheme } from '../../contexts/ThemeContext';
import { ProjectSelector } from '../ui/ProjectSelector';
import { useConfig } from '../../utils/api';

export function Header() {
    const { theme, toggleTheme } = useTheme();
    const location = useLocation();
    const { config, loading } = useConfig();

    // Generate breadcrumbs from path
    const pathnames = location.pathname.split('/').filter((x) => x);
    const isRemoteStack = !loading && config?.execution_mode === 'remote';

    return (
        <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4 flex items-center justify-between shadow-sm z-10">
            <div className="flex items-center gap-4 flex-1">
                {/* Breadcrumbs */}
                <nav className="flex items-center text-sm text-slate-500 dark:text-slate-400">
                    <Link to="/" className="hover:text-primary-600 dark:hover:text-primary-400 transition-colors">
                        <Home size={16} />
                    </Link>
                    {pathnames.length > 0 && (
                        <ChevronRight size={14} className="mx-2 text-slate-300 dark:text-slate-600" />
                    )}
                    {pathnames.map((name, index) => {
                        const routeTo = `/${pathnames.slice(0, index + 1).join('/')}`;
                        const isLast = index === pathnames.length - 1;
                        const formattedName = name.charAt(0).toUpperCase() + name.slice(1).replace(/-/g, ' ');

                        return (
                            <React.Fragment key={name}>
                                {isLast ? (
                                    <span className="font-medium text-slate-900 dark:text-white">
                                        {formattedName}
                                    </span>
                                ) : (
                                    <Link
                                        to={routeTo}
                                        className="hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
                                    >
                                        {formattedName}
                                    </Link>
                                )}
                                {!isLast && (
                                    <ChevronRight size={14} className="mx-2 text-slate-300 dark:text-slate-600" />
                                )}
                            </React.Fragment>
                        );
                    })}
                </nav>
            </div>

            <div className="flex items-center gap-4">
                {isRemoteStack && (
                    <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary-50 text-primary-800 border border-primary-100 dark:bg-primary-900/20 dark:text-primary-200 dark:border-primary-900/40">
                        <span className="flex items-center gap-1 text-xs uppercase tracking-wide font-semibold">
                            <Server size={14} /> Remote Stack
                        </span>
                        {config?.remote_ui_url && (
                            <a
                                href={config.remote_ui_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-xs font-medium hover:underline"
                            >
                                UI <ExternalLink size={12} />
                            </a>
                        )}
                        {config?.remote_server_url && (
                            <a
                                href={config.remote_server_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-xs font-medium hover:underline"
                            >
                                API <ExternalLink size={12} />
                            </a>
                        )}
                    </div>
                )}

                <ProjectSelector />

                <div className="h-6 w-px bg-slate-200 dark:bg-slate-700 mx-2" />

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
            </div>
        </header>
    );
}
