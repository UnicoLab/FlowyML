import { useEffect, useCallback, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useAIAssistant } from '../contexts/AIAssistantContext';
import { fetchApi } from '../utils/api';

/**
 * Hook to share page-specific context with the AI assistant.
 * Fetches comprehensive context from the backend API.
 * Automatically cleans up context when navigating away.
 *
 * @param {Object} options - Configuration options
 * @param {string} options.pageType - Type of page. The backend currently builds
 *   context for 'run' only; any other value returns a 400 and the hook falls
 *   back to the basic client-side context.
 * @param {string} options.resourceId - The resource ID (run_id, pipeline_name, etc.)
 * @param {boolean} options.includeLogs - Whether to include logs (default: true)
 * @param {boolean} options.includeCode - Whether to include step code (default: true)
 * @param {boolean} options.includeMetrics - Whether to include metrics (default: true)
 */
export function useAIContext({ pageType, resourceId, includeLogs = true, includeCode = true, includeMetrics = true } = {}) {
    const location = useLocation();
    const { updateContext, contextEnabled } = useAIAssistant();
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchContext = useCallback(async () => {
        if (!pageType || !resourceId || !contextEnabled) {
            return;
        }

        setIsLoading(true);
        setError(null);

        try {
            // Fetch comprehensive context from backend
            const response = await fetchApi(`/api/ai/context/${pageType}/${resourceId}?include_logs=${includeLogs}&include_code=${includeCode}&include_metrics=${includeMetrics}`);

            if (response.ok) {
                const contextData = await response.json();

                // Update context with backend data
                updateContext({
                    pageType: contextData.page_type,
                    resourceId: contextData.resource_id,
                    ...contextData.summary,
                    details: contextData.details,
                    suggestions: contextData.suggestions,
                    timestamp: new Date().toISOString()
                });
            } else {
                // Fallback: Use basic context if API fails
                console.warn('AI context API failed, using basic context');
                updateContext({
                    pageType,
                    resourceId,
                    timestamp: new Date().toISOString()
                });
            }
        } catch (err) {
            console.error('Failed to fetch AI context:', err);
            setError(err.message);

            // Fallback to basic context
            updateContext({
                pageType,
                resourceId,
                timestamp: new Date().toISOString()
            });
        } finally {
            setIsLoading(false);
        }
    }, [pageType, resourceId, contextEnabled, includeLogs, includeCode, includeMetrics, updateContext]);

    // Fetch context when enabled or resource changes
    useEffect(() => {
        if (contextEnabled && pageType && resourceId) {
            fetchContext();
        }
    }, [contextEnabled, pageType, resourceId, fetchContext]);

    // Cleanup when navigating away
    useEffect(() => {
        return () => {
            updateContext(null);
        };
    }, [location.pathname, updateContext]);

    return { isLoading, error, refetch: fetchContext };
}

/**
 * Formats run data for AI context - client-side fallback.
 * Used when backend API is not available.
 */
export function formatRunContext(run, metrics = [], selectedStep = null, logs = {}) {
    if (!run) return null;

    // Summarize steps
    const stepsSummary = run.steps ? Object.entries(run.steps).map(([name, step]) => ({
        name,
        status: step.success ? 'success' : (step.error ? 'failed' : 'pending'),
        duration: step.duration?.toFixed(2) + 's',
        cached: step.cached || false,
        error: step.error || null,
        inputs: step.inputs?.slice(0, 3),
        outputs: step.outputs?.slice(0, 3)
    })) : [];

    // Format metrics - take top 10 most relevant
    const metricsSummary = metrics.slice(0, 10).map(m => ({
        name: m.name,
        value: typeof m.value === 'number' ? m.value.toFixed(4) : m.value,
        step: m.step
    }));

    // Format logs - truncate to last 500 chars per step
    const logsSummary = {};
    if (logs && typeof logs === 'object') {
        Object.entries(logs).forEach(([stepName, stepLogs]) => {
            if (typeof stepLogs === 'string') {
                logsSummary[stepName] = stepLogs.slice(-500);
            }
        });
    }

    // Selected step details
    const selectedStepDetails = selectedStep && run.steps?.[selectedStep] ? {
        name: selectedStep,
        ...run.steps[selectedStep],
        fullError: run.steps[selectedStep].error,
        sourceCode: run.steps[selectedStep].source_code?.slice(0, 1000)
    } : null;

    return {
        pageType: 'run',
        data: {
            runId: run.run_id,
            pipelineName: run.pipeline_name,
            project: run.project,
            status: run.status,
            duration: run.duration?.toFixed(2) + 's',
            startTime: run.start_time,
            endTime: run.end_time,
            totalSteps: stepsSummary.length,
            successfulSteps: stepsSummary.filter(s => s.status === 'success').length,
            failedSteps: stepsSummary.filter(s => s.status === 'failed').length,
            cachedSteps: stepsSummary.filter(s => s.cached).length,
            steps: stepsSummary,
            metrics: metricsSummary,
            selectedStep: selectedStepDetails,
            recentLogs: logsSummary,
            environment: run.environment || {},
            context: run.context || {}
        }
    };
}

export default useAIContext;
