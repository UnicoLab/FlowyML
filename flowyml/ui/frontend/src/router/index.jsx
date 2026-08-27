import { lazy, Suspense } from 'react';
import { createBrowserRouter } from 'react-router-dom';
import { MainLayout } from '../layouts/MainLayout';

import { RequireAuth, AuthProvider } from '../contexts/AuthContext';
import { Outlet } from 'react-router-dom';

// Every page is loaded on demand. Bundling all of them together meant a
// visitor to the dashboard downloaded the code for every other screen -
// including the charting and graph libraries only a few of them use.
const Dashboard = lazy(() => import('../app/dashboard/page').then(m => ({ default: m.Dashboard })));
const Pipelines = lazy(() => import('../app/pipelines/page').then(m => ({ default: m.Pipelines })));
const Runs = lazy(() => import('../app/runs/page').then(m => ({ default: m.Runs })));
const RunDetails = lazy(() => import('../app/runs/[runId]/page').then(m => ({ default: m.RunDetails })));
const Assets = lazy(() => import('../app/assets/page').then(m => ({ default: m.Assets })));
const Experiments = lazy(() => import('../app/experiments/page').then(m => ({ default: m.Experiments })));
const ExperimentDetails = lazy(() => import('../app/experiments/[experimentId]/page').then(m => ({ default: m.ExperimentDetails })));
const Traces = lazy(() => import('../app/traces/page').then(m => ({ default: m.Traces })));
const Projects = lazy(() => import('../app/projects/page').then(m => ({ default: m.Projects })));
const ProjectDetails = lazy(() => import('../app/projects/[projectId]/page').then(m => ({ default: m.ProjectDetails })));
const Schedules = lazy(() => import('../app/schedules/page').then(m => ({ default: m.Schedules })));
const Observability = lazy(() => import('../app/observability/page').then(m => ({ default: m.Observability })));
const Leaderboard = lazy(() => import('../app/leaderboard/page').then(m => ({ default: m.Leaderboard })));
const Plugins = lazy(() => import('../app/plugins/page').then(m => ({ default: m.Plugins })));
const Settings = lazy(() => import('../app/settings/page').then(m => ({ default: m.Settings })));
const TokenManagement = lazy(() => import('../app/tokens/page').then(m => ({ default: m.TokenManagement })));
const RunComparisonPage = lazy(() => import('../app/compare/page').then(m => ({ default: m.RunComparisonPage })));
const ExperimentComparisonPage = lazy(() => import('../app/experiments/compare/page').then(m => ({ default: m.ExperimentComparisonPage })));
const DeploymentLab = lazy(() => import('../app/deployments/page').then(m => ({ default: m.DeploymentLab })));
const ModelExplorer = lazy(() => import('../app/model-explorer/page').then(m => ({ default: m.ModelExplorer })));
const Evaluations = lazy(() => import('../app/evaluations/page').then(m => ({ default: m.Evaluations })));
const EvaluationDetail = lazy(() => import('../app/evaluations/[evalId]/page').then(m => ({ default: m.EvaluationDetail })));
const EvaluationCompare = lazy(() => import('../app/evaluations/compare/page').then(m => ({ default: m.EvaluationCompare })));
const Login = lazy(() => import('../app/auth/Login').then(m => ({ default: m.Login })));

// Shown while a route's chunk is in flight.
const RouteFallback = () => (
    <div className="flex items-center justify-center h-96" role="status" aria-label="Loading page">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
    </div>
);

// Layout Wrapper to provide Auth Context
const AppLayout = () => (
    <AuthProvider>
        <Suspense fallback={<RouteFallback />}>
            <Outlet />
        </Suspense>
    </AuthProvider>
);

export const router = createBrowserRouter([
    {
        element: <AppLayout />, // Wrap everything in AuthProvider
        children: [
            {
                path: '/login',
                element: <Login />,
            },
            {
                path: '/',
                element: (
                    <RequireAuth>
                        <MainLayout />
                    </RequireAuth>
                ),
                children: [
                    { index: true, element: <Dashboard /> },
                    { path: 'pipelines', element: <Pipelines /> },
                    { path: 'runs', element: <Runs /> },
                    { path: 'compare', element: <RunComparisonPage /> },
                    { path: 'runs/:runId', element: <RunDetails /> },
                    { path: 'assets', element: <Assets /> },
                    { path: 'experiments', element: <Experiments /> },
                    { path: 'evaluations', element: <Evaluations /> },
                    { path: 'evaluations/compare', element: <EvaluationCompare /> },
                    { path: 'evaluations/:evalId', element: <EvaluationDetail /> },
                    { path: 'experiments/compare', element: <ExperimentComparisonPage /> },
                    { path: 'experiments/:experimentId', element: <ExperimentDetails /> },
                    { path: 'traces', element: <Traces /> },
                    { path: 'projects', element: <Projects /> },
                    { path: 'projects/:projectId', element: <ProjectDetails /> },
                    { path: 'schedules', element: <Schedules /> },
                    { path: 'observability', element: <Observability /> },
                    { path: 'leaderboard', element: <Leaderboard /> },
                    { path: 'plugins', element: <Plugins /> },
                    { path: 'settings', element: <Settings /> },
                    { path: 'tokens', element: <TokenManagement /> },
                    { path: 'deployments', element: <DeploymentLab /> },
                    { path: 'model-explorer', element: <ModelExplorer /> },
                ],
            },
        ],
    },
]);
