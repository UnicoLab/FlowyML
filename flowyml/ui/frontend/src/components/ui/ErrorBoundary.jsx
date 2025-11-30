import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Button';

export class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        // Update state so the next render will show the fallback UI.
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        // You can also log the error to an error reporting service
        console.error("Uncaught error:", error, errorInfo);
        this.setState({ errorInfo });
    }

    handleReset = () => {
        this.setState({ hasError: false, error: null, errorInfo: null });
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
                <div className="p-6 rounded-xl bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 text-center">
                    <div className="flex justify-center mb-4">
                        <div className="p-3 bg-red-100 dark:bg-red-800/30 rounded-full">
                            <AlertTriangle className="w-8 h-8 text-red-600 dark:text-red-400" />
                        </div>
                    </div>
                    <h3 className="text-lg font-semibold text-red-900 dark:text-red-200 mb-2">
                        Something went wrong
                    </h3>
                    <p className="text-red-700 dark:text-red-300 mb-6 max-w-md mx-auto">
                        {this.state.error?.message || "An unexpected error occurred while rendering this component."}
                    </p>
                    <Button
                        onClick={this.handleReset}
                        variant="outline"
                        className="border-red-200 hover:bg-red-100 dark:border-red-800 dark:hover:bg-red-900/30 text-red-700 dark:text-red-300"
                    >
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Try Again
                    </Button>
                </div>
            );
        }

        return this.props.children;
    }
}
