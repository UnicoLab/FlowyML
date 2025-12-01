import React from 'react';
import { RefreshCw, Bug, Terminal } from 'lucide-react';
import { Button } from './Button';

export class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null, reported: false };
    }

    static getDerivedStateFromError(error) {
        // Update state so the next render will show the fallback UI.
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        console.error("Uncaught error:", error, errorInfo);
        this.setState({ errorInfo });

        // Report to backend
        this.reportError(error, errorInfo);
    }

    reportError = async (error, errorInfo) => {
        if (this.state.reported) return;

        try {
            // Use relative URL to work with proxy or same origin
            await fetch('/api/client/errors', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: error.message || 'Unknown error',
                    stack: error.stack,
                    component_stack: errorInfo?.componentStack,
                    url: window.location.href,
                    user_agent: navigator.userAgent
                }),
            });
            this.setState({ reported: true });
        } catch (e) {
            console.error("Failed to report error:", e);
        }
    }

    handleReset = () => {
        this.setState({ hasError: false, error: null, errorInfo: null, reported: false });
        if (this.props.onReset) {
            this.props.onReset();
        }
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div className="min-h-[400px] flex items-center justify-center p-6 w-full">
                    <div className="max-w-lg w-full bg-white dark:bg-gray-900 rounded-2xl shadow-xl overflow-hidden border border-gray-200 dark:border-gray-800">
                        <div className="bg-gradient-to-r from-pink-500 via-red-500 to-yellow-500 h-2"></div>
                        <div className="p-8">
                            <div className="flex justify-center mb-6">
                                <div className="relative">
                                    <div className="absolute inset-0 bg-red-100 dark:bg-red-900/30 rounded-full animate-ping opacity-75"></div>
                                    <div className="relative p-4 bg-red-50 dark:bg-red-900/20 rounded-full">
                                        <Bug className="w-12 h-12 text-red-500 dark:text-red-400" />
                                    </div>
                                </div>
                            </div>

                            <h2 className="text-2xl font-bold text-center text-gray-900 dark:text-white mb-2">
                                Well, this is awkward...
                            </h2>

                            <p className="text-center text-gray-600 dark:text-gray-400 mb-6">
                                The hamsters powering this component decided to take an unscheduled nap.
                                We've dispatched a team of digital veterinarians (aka developers) to wake them up.
                            </p>

                            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 mb-6 font-mono text-xs text-left overflow-auto max-h-32 border border-gray-200 dark:border-gray-700">
                                <div className="flex items-center text-red-500 mb-2">
                                    <Terminal className="w-3 h-3 mr-2" />
                                    <span className="font-semibold">Error Log</span>
                                </div>
                                <code className="text-gray-700 dark:text-gray-300 break-all whitespace-pre-wrap">
                                    {this.state.error?.message || "Unknown error"}
                                </code>
                            </div>

                            <div className="flex justify-center gap-4">
                                <Button
                                    onClick={() => window.location.reload()}
                                    variant="outline"
                                    className="border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
                                >
                                    Reload Page
                                </Button>
                                <Button
                                    onClick={this.handleReset}
                                    className="bg-gradient-to-r from-red-500 to-pink-600 hover:from-red-600 hover:to-pink-700 text-white border-0"
                                >
                                    <RefreshCw className="w-4 h-4 mr-2" />
                                    Try Again
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
