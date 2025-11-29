

import React from 'react';
import { RouterProvider } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { ProjectProvider } from './contexts/ProjectContext';
import { router } from './router';

function App() {
    return (
        <ThemeProvider>
            <ProjectProvider>
                <RouterProvider router={router} />
            </ProjectProvider>
        </ThemeProvider>
    );
}



export default App
