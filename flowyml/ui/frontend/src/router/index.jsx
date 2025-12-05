import { createBrowserRouter } from 'react-router-dom';
import { MainLayout } from '../layouts/MainLayout';
import { Dashboard } from '../app/dashboard/page';
import { Pipelines } from '../app/pipelines/page';
import { Runs } from '../app/runs/page';
import { RunDetails } from '../app/runs/[runId]/page';
import { Assets } from '../app/assets/page';
import { Experiments } from '../app/experiments/page';
import { ExperimentDetails } from '../app/experiments/[experimentId]/page';
import { Traces } from '../app/traces/page';
import { Projects } from '../app/projects/page';
import { ProjectDetails } from '../app/projects/[projectId]/page';
import { Schedules } from '../app/schedules/page';
import { Observability } from '../app/observability/page';
import { Leaderboard } from '../app/leaderboard/page';
import { Plugins } from '../app/plugins/page';
import { Settings } from '../app/settings/page';
import { TokenManagement } from '../app/tokens/page';
import { RunComparisonPage } from '../app/compare/page';
import { ExperimentComparisonPage } from '../app/experiments/compare/page';

export const router = createBrowserRouter([
    {
        path: '/',
        element: <MainLayout />,
        children: [
            { index: true, element: <Dashboard /> },
            { path: 'pipelines', element: <Pipelines /> },
            { path: 'runs', element: <Runs /> },
            { path: 'compare', element: <RunComparisonPage /> },
            { path: 'runs/:runId', element: <RunDetails /> },
            { path: 'assets', element: <Assets /> },
            { path: 'experiments', element: <Experiments /> },
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
        ],
    },
]);
