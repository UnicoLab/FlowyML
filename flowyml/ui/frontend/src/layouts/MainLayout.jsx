import React, { lazy, Suspense, useState, useEffect, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '../components/sidebar/Sidebar';
import { Header } from '../components/header/Header';

import { ErrorBoundary } from '../components/ui/ErrorBoundary';
import { AIAssistantButton } from '../components/ai/AIAssistantButton';
import { useAIAssistant } from '../contexts/AIAssistantContext';

// The assistant panel pulls in the markdown renderer and syntax highlighter,
// which together are larger than the rest of the application shell. It is a
// closed overlay on every page load, so its code is fetched the first time a
// user actually opens it.
const AIAssistantPanel = lazy(() =>
    import('../components/ai/AIAssistantPanel').then(m => ({ default: m.AIAssistantPanel })),
);

const MOBILE_BREAKPOINT = 768;

/**
 * Mounts the assistant panel once it has been opened, and keeps it mounted
 * afterwards so its open/close transitions still run.
 */
function AIAssistantOverlay() {
    const { isOpen } = useAIAssistant();
    const [hasOpened, setHasOpened] = useState(false);

    useEffect(() => {
        if (isOpen) setHasOpened(true);
    }, [isOpen]);

    if (!hasOpened) return null;

    return (
        <Suspense fallback={null}>
            <AIAssistantPanel />
        </Suspense>
    );
}

function useIsMobile() {
    const [isMobile, setIsMobile] = useState(
        typeof window !== 'undefined' ? window.innerWidth < MOBILE_BREAKPOINT : false
    );

    useEffect(() => {
        const onResize = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
        window.addEventListener('resize', onResize);
        return () => window.removeEventListener('resize', onResize);
    }, []);

    return isMobile;
}

export function MainLayout() {
    const isMobile = useIsMobile();
    const [collapsed, setCollapsed] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);

    // Auto-collapse sidebar on mobile
    useEffect(() => {
        if (isMobile) {
            setCollapsed(true);
            setMobileOpen(false);
        }
    }, [isMobile]);

    const toggleMobileSidebar = useCallback(() => {
        setMobileOpen(prev => !prev);
    }, []);

    const closeMobileSidebar = useCallback(() => {
        setMobileOpen(false);
    }, []);

    return (
        <div className="flex h-screen bg-slate-50 dark:bg-slate-900 overflow-hidden">
            {/* Mobile Sidebar Backdrop */}
            {isMobile && mobileOpen && (
                <div
                    className="sidebar-backdrop animate-fade-in"
                    onClick={closeMobileSidebar}
                    aria-hidden="true"
                />
            )}

            {/* Sidebar */}
            <Sidebar
                collapsed={collapsed}
                setCollapsed={setCollapsed}
                isMobile={isMobile}
                mobileOpen={mobileOpen}
                onMobileClose={closeMobileSidebar}
            />

            <div className="flex-1 flex flex-col min-w-0">
                <Header
                    isMobile={isMobile}
                    onMenuClick={toggleMobileSidebar}
                />
                <main className="flex-1 overflow-y-auto p-4 md:p-6 scrollbar-thin">
                    <div className="w-full max-w-[1800px] mx-auto">
                        <ErrorBoundary>
                            <Outlet />
                        </ErrorBoundary>
                    </div>
                </main>
            </div>

            {/* AI Assistant - Floating button and slide-out panel */}
            <AIAssistantButton />
            <AIAssistantOverlay />
        </div>
    );
}
