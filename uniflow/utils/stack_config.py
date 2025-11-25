"""
Configuration loader for UniFlow stacks.

Loads stack configurations from YAML files, environment variables,
and provides defaults.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class StackConfigFile:
    """
    Stack configuration loaded from uniflow.yaml.
    
    Example uniflow.yaml:
    ```yaml
    stacks:
      local:
        type: local
        artifact_store:
          path: .uniflow/artifacts
        metadata_store:
          path: .uniflow/metadata.db
      
      production:
        type: gcp
        project_id: ${GCP_PROJECT_ID}
        region: us-central1
        artifact_store:
          type: gcs
          bucket: ${GCP_BUCKET}
        container_registry:
          type: gcr
          uri: gcr.io/${GCP_PROJECT_ID}
        orchestrator:
          type: vertex_ai
    
    resources:
      default:
        cpu: "2"
        memory: "8Gi"
      
      gpu_training:
        cpu: "8"
        memory: "32Gi"
        gpu: nvidia-tesla-v100
        gpu_count: 2
    
    docker:
      dockerfile: ./Dockerfile
      build_context: .
      use_poetry: true
      requirements_file: requirements.txt
    ```
    """
    
    stacks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    resources: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    docker: Dict[str, Any] = field(default_factory=dict)
    default_stack: Optional[str] = None


class ConfigLoader:
    """Load and manage UniFlow configurations."""
    
    DEFAULT_CONFIG_FILES = [
        "uniflow.yaml",
        "uniflow.yml",
        ".uniflow/config.yaml",
        ".uniflow/config.yml",
    ]
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader.
        
        Args:
            config_path: Path to configuration file. If None, searches default locations.
        """
        self.config_path = self._find_config_file(config_path)
        self.config: Optional[StackConfigFile] = None
        
        if self.config_path:
            self.load()
    
    def _find_config_file(self, config_path: Optional[str] = None) -> Optional[Path]:
        """Find configuration file."""
        if config_path:
            path = Path(config_path)
            if path.exists():
                return path
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        # Search default locations
        for default_path in self.DEFAULT_CONFIG_FILES:
            path = Path(default_path)
            if path.exists():
                return path
        
        return None
    
    def load(self) -> StackConfigFile:
        """Load configuration from file."""
        if not self.config_path:
            # Return empty config
            self.config = StackConfigFile()
            return self.config
        
        with open(self.config_path, 'r') as f:
            data = yaml.safe_load(f) or {}
        
        # Expand environment variables
        data = self._expand_env_vars(data)
        
        self.config = StackConfigFile(
            stacks=data.get('stacks', {}),
            resources=data.get('resources', {}),
            docker=data.get('docker', {}),
            default_stack=data.get('default_stack')
        )
        
        return self.config
    
    def _expand_env_vars(self, data: Any) -> Any:
        """Recursively expand environment variables in config."""
        if isinstance(data, dict):
            return {k: self._expand_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._expand_env_vars(item) for item in data]
        elif isinstance(data, str):
            # Expand ${VAR} or $VAR
            import re
            def replace_var(match):
                var_name = match.group(1) or match.group(2)
                return os.getenv(var_name, match.group(0))
            
            pattern = r'\$\{([^}]+)\}|\$([A-Z_][A-Z0-9_]*)'
            return re.sub(pattern, replace_var, data)
        else:
            return data
    
    def get_stack_config(self, stack_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific stack."""
        if not self.config:
            return None
        return self.config.stacks.get(stack_name)
    
    def get_resource_config(self, resource_name: str = "default") -> Optional[Dict[str, Any]]:
        """Get resource configuration."""
        if not self.config:
            return None
        return self.config.resources.get(resource_name)
    
    def get_docker_config(self) -> Dict[str, Any]:
        """Get Docker configuration."""
        if not self.config:
            return self._get_default_docker_config()
        return self.config.docker or self._get_default_docker_config()
    
    def _get_default_docker_config(self) -> Dict[str, Any]:
        """Get default Docker configuration."""
        # Auto-detect Dockerfile
        dockerfile = None
        for possible_dockerfile in ["Dockerfile", "docker/Dockerfile", ".docker/Dockerfile"]:
            if Path(possible_dockerfile).exists():
                dockerfile = possible_dockerfile
                break
        
        # Check for poetry
        use_poetry = Path("pyproject.toml").exists()
        
        # Check for requirements.txt
        requirements_file = "requirements.txt" if Path("requirements.txt").exists() else None
        
        return {
            "dockerfile": dockerfile,
            "build_context": ".",
            "use_poetry": use_poetry,
            "requirements_file": requirements_file,
            "base_image": "python:3.11-slim",
        }
    
    def list_stacks(self) -> List[str]:
        """List all configured stacks."""
        if not self.config:
            return []
        return list(self.config.stacks.keys())
    
    def get_default_stack(self) -> Optional[str]:
        """Get the default stack name."""
        if not self.config:
            return None
        return self.config.default_stack or (
            list(self.config.stacks.keys())[0] if self.config.stacks else None
        )


def load_config(config_path: Optional[str] = None) -> ConfigLoader:
    """
    Load UniFlow configuration.
    
    Args:
        config_path: Path to config file. If None, searches default locations.
        
    Returns:
        ConfigLoader instance
    """
    return ConfigLoader(config_path)


def create_stack_from_config(config: Dict[str, Any], name: str):
    """
    Create a stack instance from configuration dictionary.
    
    Args:
        config: Stack configuration dictionary
        name: Stack name
        
    Returns:
        Stack instance
    """
    stack_type = config.get('type', 'local')
    
    if stack_type == 'local':
        from uniflow.stacks.local import LocalStack
        return LocalStack(
            name=name,
            artifact_path=config.get('artifact_store', {}).get('path', '.uniflow/artifacts'),
            metadata_path=config.get('metadata_store', {}).get('path', '.uniflow/metadata.db'),
        )
    
    elif stack_type == 'gcp':
        from uniflow.stacks.gcp import GCPStack
        return GCPStack(
            name=name,
            project_id=config.get('project_id'),
            region=config.get('region', 'us-central1'),
            bucket_name=config.get('artifact_store', {}).get('bucket'),
            registry_uri=config.get('container_registry', {}).get('uri'),
            service_account=config.get('orchestrator', {}).get('service_account'),
        )
    
    else:
        raise ValueError(f"Unknown stack type: {stack_type}")


def create_resource_config_from_dict(config: Dict[str, Any]):
    """Create ResourceConfig from dictionary."""
    from uniflow.stacks.components import ResourceConfig
    return ResourceConfig(**config)


def create_docker_config_from_dict(config: Dict[str, Any]):
    """Create DockerConfig from dictionary."""
    from uniflow.stacks.components import DockerConfig
    
    # Handle poetry configuration
    if config.get('use_poetry'):
        # Read dependencies from pyproject.toml
        import toml
        try:
            with open('pyproject.toml', 'r') as f:
                pyproject = toml.load(f)
            
            # Extract dependencies
            deps = pyproject.get('tool', {}).get('poetry', {}).get('dependencies', {})
            requirements = [
                f"{name}>={version.replace('^', '')}" 
                for name, version in deps.items() 
                if name != 'python' and isinstance(version, str)
            ]
            config['requirements'] = requirements
        except:
            pass
    
    # Handle requirements file
    elif config.get('requirements_file'):
        try:
            with open(config['requirements_file'], 'r') as f:
                requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            config['requirements'] = requirements
        except:
            pass
    
    return DockerConfig(
        image=config.get('image'),
        dockerfile=config.get('dockerfile'),
        build_context=config.get('build_context', '.'),
        requirements=config.get('requirements'),
        base_image=config.get('base_image', 'python:3.11-slim'),
        env_vars=config.get('env_vars', {}),
        build_args=config.get('build_args', {}),
    )
