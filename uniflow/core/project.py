"""
Multi-tenancy and project organization.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

class Project:
    """
    Project for organizing pipelines, runs, and artifacts.
    
    Provides multi-tenancy and better organization.
    
    Examples:
        >>> from uniflow import Project, Pipeline, step
        >>> 
        >>> # Create project
        >>> project = Project("recommendation_system")
        >>> 
        >>> # Create pipeline in project
        >>> pipeline = project.create_pipeline("training")
        >>> pipeline.add_step(...)
        >>> result = pipeline.run()
        >>> 
        >>> # List all runs in project
        >>> runs = project.list_runs()
        >>> 
        >>> # Get artifacts
        >>> artifacts = project.get_artifacts()
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        projects_dir: str = ".uniflow/projects"
    ):
        self.name = name
        self.description = description
        
        # Project directory
        self.project_dir = Path(projects_dir) / name
        self.project_dir.mkdir(parents=True, exist_ok=True)
        
        # Sub-directories
        self.pipelines_dir = self.project_dir / "pipelines"
        self.pipelines_dir.mkdir(exist_ok=True)
        
        self.runs_dir = self.project_dir / "runs"
        self.runs_dir.mkdir(exist_ok=True)
        
        self.artifacts_dir = self.project_dir / "artifacts"
        self.artifacts_dir.mkdir(exist_ok=True)
        
        # Metadata
        self.metadata_file = self.project_dir / "project.json"
        self._load_or_create_metadata()
        
        # Storage
        from uniflow.storage.metadata import SQLiteMetadataStore
        db_path = str(self.project_dir / "metadata.db")
        self.metadata_store = SQLiteMetadataStore(db_path)
        
    def _load_or_create_metadata(self):
        """Load or create project metadata."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                'name': self.name,
                'description': self.description,
                'created_at': datetime.now().isoformat(),
                'pipelines': [],
                'tags': {}
            }
            self._save_metadata()
            
    def _save_metadata(self):
        """Save project metadata."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
            
    def create_pipeline(self, name: str, **kwargs) -> 'Pipeline':
        """
        Create a pipeline in this project.
        
        Args:
            name: Pipeline name
            **kwargs: Additional arguments for Pipeline
            
        Returns:
            Pipeline instance
        """
        from uniflow.core.pipeline import Pipeline
        
        # Create pipeline with project-specific settings
        pipeline = Pipeline(
            name=name,
            cache_dir=str(self.artifacts_dir / "cache"),
            **kwargs
        )
        
        # Override runs directory to project runs
        pipeline.runs_dir = self.runs_dir
        
        # Use project metadata store
        pipeline.metadata_store = self.metadata_store
        
        # Register pipeline
        if name not in self.metadata['pipelines']:
            self.metadata['pipelines'].append(name)
            self._save_metadata()
            
        print(f"📁 Created pipeline '{name}' in project '{self.name}'")
        return pipeline
        
    def list_runs(
        self,
        pipeline_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all runs in this project.
        
        Args:
            pipeline_name: Filter by pipeline name
            limit: Maximum number of runs
            
        Returns:
            List of run metadata
        """
        if pipeline_name:
            runs = self.metadata_store.query(pipeline_name=pipeline_name)
        else:
            runs = self.metadata_store.list_runs(limit=limit)
            
        return runs
        
    def get_artifacts(
        self,
        artifact_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get artifacts in this project.
        
        Args:
            artifact_type: Filter by type
            limit: Maximum number of artifacts
            
        Returns:
            List of artifact metadata
        """
        filters = {}
        if artifact_type:
            filters['type'] = artifact_type
            
        return self.metadata_store.list_assets(limit=limit, **filters)
        
    def get_pipelines(self) -> List[str]:
        """Get list of pipelines in this project."""
        return self.metadata['pipelines']
        
    def get_stats(self) -> Dict[str, Any]:
        """Get project statistics."""
        stats = self.metadata_store.get_statistics()
        stats['project_name'] = self.name
        stats['pipelines'] = len(self.metadata['pipelines'])
        return stats
        
    def add_tag(self, key: str, value: str):
        """Add a tag to the project."""
        self.metadata['tags'][key] = value
        self._save_metadata()
        
    def get_tags(self) -> Dict[str, str]:
        """Get project tags."""
        return self.metadata['tags']
        
    def export_metadata(self, output_file: str):
        """Export project metadata."""
        export_data = {
            'project': self.metadata,
            'runs': self.list_runs(),
            'artifacts': self.get_artifacts(),
            'stats': self.get_stats()
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
            
        print(f"📤 Exported project metadata to {output_file}")
        
    def __repr__(self) -> str:
        return f"Project(name='{self.name}', pipelines={len(self.metadata['pipelines'])})"

class ProjectManager:
    """
    Manage multiple projects.
    
    Examples:
        >>> from uniflow import ProjectManager
        >>> 
        >>> manager = ProjectManager()
        >>> 
        >>> # Create projects
        >>> rec_sys = manager.create_project("recommendation_system")
        >>> fraud = manager.create_project("fraud_detection")
        >>> 
        >>> # List all projects
        >>> projects = manager.list_projects()
        >>> 
        >>> # Get project
        >>> project = manager.get_project("recommendation_system")
    """
    
    def __init__(self, projects_dir: str = ".uniflow/projects"):
        self.projects_dir = Path(projects_dir)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        
    def create_project(self, name: str, description: str = "") -> Project:
        """Create a new project."""
        # Fix: Pass the projects directory itself, not the parent
        project = Project(name, description, str(self.projects_dir))
        print(f"✨ Created project: {name}")
        return project
        
    def get_project(self, name: str) -> Optional[Project]:
        """Get an existing project."""
        project_dir = self.projects_dir / name
        if not project_dir.exists():
            return None
        # Fix: Pass the projects directory itself
        return Project(name, projects_dir=str(self.projects_dir))
        
    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects."""
        projects = []
        if not self.projects_dir.exists():
            return projects
            
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                metadata_file = project_dir / "project.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            projects.append(metadata)
                    except Exception as e:
                        print(f"⚠️  Failed to load project metadata for {project_dir.name}: {e}")
        return projects
        
    def delete_project(self, name: str, confirm: bool = False):
        """Delete a project (requires confirmation)."""
        if not confirm:
            print(f"⚠️  Project deletion requires confirmation. Set confirm=True")
            return
            
        project_dir = self.projects_dir / name
        if project_dir.exists():
            import shutil
            shutil.rmtree(project_dir)
            print(f"🗑️  Deleted project: {name}")
