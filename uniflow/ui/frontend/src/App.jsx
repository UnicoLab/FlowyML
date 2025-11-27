import React, { useEffect, useState } from 'react'
import { Routes, Route, Link, useParams } from 'react-router-dom'
import { LayoutDashboard, Activity, Database, Settings, Play, ArrowRight, Box, FileText, Layers, FlaskConical, BarChart2 } from 'lucide-react'
import { ThemeProvider } from './contexts/ThemeContext'
import { ProjectProvider } from './contexts/ProjectContext'
import { Layout } from './components/Layout'
import { Card, CardHeader, CardTitle, CardContent } from './components/ui/Card'
import { Badge } from './components/ui/Badge'
import { Button } from './components/ui/Button'
import { Dashboard } from './components/Dashboard'
import { Pipelines } from './components/Pipelines'
import { Runs } from './components/Runs'
import { RunDetails } from './components/RunDetails'
import { Assets } from './components/Assets'
import { Experiments } from './components/Experiments'
import { ExperimentDetails } from './components/ExperimentDetails'
import { Settings as SettingsPage } from './components/Settings'
import Traces from './components/Traces';
import Projects from './components/Projects';
import Schedules from './components/Schedules';
import Leaderboard from './components/Leaderboard';
import { format } from 'date-fns'

function App() {
    return (
        <ThemeProvider>
            <ProjectProvider>
                <Layout>
                    <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/pipelines" element={<Pipelines />} />
                        <Route path="/runs" element={<Runs />} />
                        <Route path="/runs/:runId" element={<RunDetails />} />
                        <Route path="/assets" element={<Assets />} />
                        <Route path="/experiments" element={<Experiments />} />
                        <Route path="/experiments/:experimentId" element={<ExperimentDetails />} />
                        <Route path="/traces" element={<Traces />} />
                        <Route path="/projects" element={<Projects />} />
                        <Route path="/schedules" element={<Schedules />} />
                        <Route path="/leaderboard" element={<Leaderboard />} />
                        <Route path="/settings" element={<SettingsPage />} />
                    </Routes>
                </Layout>
            </ProjectProvider>
        </ThemeProvider>
    )
}



export default App
