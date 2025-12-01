

import React from 'react';
import { RouterProvider } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { ProjectProvider } from './contexts/ProjectContext';
import { ToastProvider } from './contexts/ToastContext';
import { router } from './router';

function App() {
    return (
        <ThemeProvider>
            <ProjectProvider>
                <ToastProvider>
                    <RouterProvider router={router} />
                </ToastProvider>
            </ProjectProvider>
        </ThemeProvider>
    );
}



export default App
