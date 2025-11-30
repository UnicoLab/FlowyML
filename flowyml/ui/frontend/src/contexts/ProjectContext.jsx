import React, { createContext, useContext, useState, useEffect } from 'react';

const ProjectContext = createContext();

export function ProjectProvider({ children }) {
    const [selectedProject, setSelectedProject] = useState(() => {
        // Check localStorage first
        const saved = localStorage.getItem('flowyml-selected-project');
        return saved || null; // null means "All Projects"
    });

    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Fetch available projects
        fetch('/api/projects/')
            .then(res => res.json())
            .then(data => {
                setProjects(data.projects || []);
                setLoading(false);
            })
            .catch(err => {
                console.error('Failed to fetch projects:', err);
                setLoading(false);
            });
    }, []);

    useEffect(() => {
        // Save to localStorage
        if (selectedProject) {
            localStorage.setItem('flowyml-selected-project', selectedProject);
        } else {
            localStorage.removeItem('flowyml-selected-project');
        }
    }, [selectedProject]);

    const selectProject = (projectName) => {
        setSelectedProject(projectName);
    };

    const clearProject = () => {
        setSelectedProject(null);
    };

    const refreshProjects = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/projects/');
            const data = await res.json();
            setProjects(data.projects || []);
        } catch (err) {
            console.error('Failed to refresh projects:', err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <ProjectContext.Provider value={{
            selectedProject,
            projects,
            loading,
            selectProject,
            clearProject,
            refreshProjects
        }}>
            {children}
        </ProjectContext.Provider>
    );
}

export function useProject() {
    const context = useContext(ProjectContext);
    if (!context) {
        throw new Error('useProject must be used within ProjectProvider');
    }
    return context;
}
