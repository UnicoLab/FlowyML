

import React from 'react';
import { RouterProvider } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { ProjectProvider } from './contexts/ProjectContext';
import { ToastProvider } from './contexts/ToastContext';
import { AIAssistantProvider } from './contexts/AIAssistantContext';
import { router } from './router';

function App() {
    return (
        <AIAssistantProvider>
            <ThemeProvider>
                <ProjectProvider>
                    <ToastProvider>
                        <RouterProvider router={router} />
                    </ToastProvider>
                </ProjectProvider>
            </ThemeProvider>
        </AIAssistantProvider>
    );
}



export default App
