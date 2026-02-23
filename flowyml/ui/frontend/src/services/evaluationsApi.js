/**
 * FlowyML Evaluations API Service
 *
 * Thin wrapper around fetchApi for the evaluations backend endpoints.
 */
import { fetchApi } from '../utils/api';

/**
 * Run an evaluation with specified scorers.
 */
export async function runEvaluation({ data, scorers, experiment, threshold, datasetName }) {
    const res = await fetchApi('/api/evaluations/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            data,
            scorers,
            experiment: experiment || undefined,
            threshold: threshold || undefined,
            dataset_name: datasetName || undefined,
        }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Evaluation failed (${res.status})`);
    }
    return res.json();
}

/**
 * Get detailed results for a single evaluation run.
 */
export async function getEvalResult(evalId) {
    const res = await fetchApi(`/api/evaluations/results/${evalId}`);
    if (!res.ok) throw new Error(`Eval ${evalId} not found`);
    return res.json();
}

/**
 * List recent evaluations, optionally filtered by experiment.
 */
export async function listEvaluations({ experiment, limit = 20 } = {}) {
    const params = new URLSearchParams();
    if (experiment) params.set('experiment', experiment);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    const res = await fetchApi(`/api/evaluations/list${qs ? `?${qs}` : ''}`);
    if (!res.ok) throw new Error('Failed to list evaluations');
    return res.json();
}

/**
 * Compare two or more evaluation runs.
 */
export async function compareEvaluations(evalIds, threshold = 0.05) {
    const res = await fetchApi('/api/evaluations/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ eval_ids: evalIds, threshold }),
    });
    if (!res.ok) throw new Error('Comparison failed');
    return res.json();
}

/**
 * Get all available scorers, optionally filtered by type.
 */
export async function getAvailableScorers(scorerType) {
    const qs = scorerType ? `?scorer_type=${scorerType}` : '';
    const res = await fetchApi(`/api/evaluations/scorers${qs}`);
    if (!res.ok) throw new Error('Failed to fetch scorers');
    return res.json();
}
