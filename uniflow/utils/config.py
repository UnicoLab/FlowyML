"""Configuration management for UniFlow."""

import os
import yaml
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field


@dataclass
class UniFlowConfig:
    """Global UniFlow configuration."""

    # Storage paths
    uniflow_home: Path = field(default_factory=lambda: Path.home() / ".uniflow")
    artifacts_dir: Path = field(default_factory=lambda: Path(".uniflow/artifacts"))
    metadata_db: Path = field(default_factory=lambda: Path(".uniflow/metadata.db"))
    cache_dir: Path = field(default_factory=lambda: Path(".uniflow/cache"))
    runs_dir: Path = field(default_factory=lambda: Path(".uniflow/runs"))
    experiments_dir: Path = field(default_factory=lambda: Path(".uniflow/experiments"))

    # Execution settings
    default_stack: str = "local"
    execution_mode: str = "local"  # local or remote
    remote_server_url: str = ""
    remote_ui_url: str = ""
    enable_caching: bool = True
    enable_logging: bool = True
    log_level: str = "INFO"
    max_cache_size_mb: int = 10000  # 10GB default

    # UI settings
    ui_host: str = "localhost"
    ui_port: int = 8080
    enable_ui: bool = False

    # Experiment tracking
    auto_log_params: bool = True
    auto_log_metrics: bool = True
    auto_log_artifacts: bool = True
    track_git: bool = True
    track_environment: bool = True

    # Performance settings
    max_parallel_steps: int = 4
    step_timeout_seconds: int = 3600  # 1 hour default
    retry_max_attempts: int = 3

    # Advanced settings
    debug_mode: bool = False
    strict_validation: bool = True
    allow_pickle: bool = True

    def __post_init__(self):
        """Ensure all paths are Path objects."""
        for field_name in [
            "uniflow_home",
            "artifacts_dir",
            "metadata_db",
            "cache_dir",
            "runs_dir",
            "experiments_dir",
        ]:
            value = getattr(self, field_name)
            if not isinstance(value, Path):
                setattr(self, field_name, Path(value))

    def create_directories(self) -> None:
        """Create necessary directories."""
        self.uniflow_home.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.experiments_dir.mkdir(parents=True, exist_ok=True)

        # Create metadata db parent dir
        self.metadata_db.parent.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "uniflow_home": str(self.uniflow_home),
            "artifacts_dir": str(self.artifacts_dir),
            "metadata_db": str(self.metadata_db),
            "cache_dir": str(self.cache_dir),
            "runs_dir": str(self.runs_dir),
            "experiments_dir": str(self.experiments_dir),
            "default_stack": self.default_stack,
            "execution_mode": self.execution_mode,
            "remote_server_url": self.remote_server_url,
            "remote_ui_url": self.remote_ui_url,
            "enable_caching": self.enable_caching,
            "enable_logging": self.enable_logging,
            "log_level": self.log_level,
            "max_cache_size_mb": self.max_cache_size_mb,
            "ui_host": self.ui_host,
            "ui_port": self.ui_port,
            "enable_ui": self.enable_ui,
            "auto_log_params": self.auto_log_params,
            "auto_log_metrics": self.auto_log_metrics,
            "auto_log_artifacts": self.auto_log_artifacts,
            "track_git": self.track_git,
            "track_environment": self.track_environment,
            "max_parallel_steps": self.max_parallel_steps,
            "step_timeout_seconds": self.step_timeout_seconds,
            "retry_max_attempts": self.retry_max_attempts,
            "debug_mode": self.debug_mode,
            "strict_validation": self.strict_validation,
            "allow_pickle": self.allow_pickle,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UniFlowConfig":
        """Create config from dictionary."""
        return cls(**data)

    def save(self, path: Path | None = None) -> None:
        """Save config to file.

        Args:
            path: Path to save config (defaults to ~/.uniflow/config.yaml)
        """
        if path is None:
            path = self.uniflow_home / "config.yaml"

        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)

    @classmethod
    def load(cls, path: Path | None = None) -> "UniFlowConfig":
        """Load config from file.

        Args:
            path: Path to load config from (defaults to ~/.uniflow/config.yaml)

        Returns:
            Loaded UniFlowConfig instance
        """
        if path is None:
            path = Path.home() / ".uniflow" / "config.yaml"

        if not path.exists():
            # Return default config
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)


# Global config instance
_global_config: UniFlowConfig | None = None


def get_config() -> UniFlowConfig:
    """Get global UniFlow configuration.

    Returns:
        Global UniFlowConfig instance
    """
    global _global_config

    if _global_config is None:
        # Try to load from environment variable
        config_path = os.environ.get("UNIFLOW_CONFIG")
        if config_path:
            _global_config = UniFlowConfig.load(Path(config_path))
        else:
            # Load from default location
            _global_config = UniFlowConfig.load()

        # Create necessary directories
        _global_config.create_directories()

    return _global_config


def set_config(config: UniFlowConfig) -> None:
    """Set global UniFlow configuration.

    Args:
        config: UniFlowConfig instance to set as global
    """
    global _global_config
    _global_config = config
    _global_config.create_directories()


def reset_config() -> None:
    """Reset global configuration to defaults."""
    global _global_config
    _global_config = UniFlowConfig()
    _global_config.create_directories()


def update_config(**kwargs) -> None:
    """Update global configuration with new values.

    Args:
        **kwargs: Configuration values to update
    """
    config = get_config()
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)


def load_project_config(project_dir: Path | None = None) -> dict[str, Any]:
    """Load project-specific configuration.

    Args:
        project_dir: Project directory (defaults to current directory)

    Returns:
        Project configuration dictionary
    """
    if project_dir is None:
        project_dir = Path.cwd()

    config_path = project_dir / "uniflow.yaml"
    if not config_path.exists():
        config_path = project_dir / "uniflow.yml"

    if not config_path.exists():
        return {}

    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def save_project_config(config: dict[str, Any], project_dir: Path | None = None) -> None:
    """Save project-specific configuration.

    Args:
        config: Configuration dictionary
        project_dir: Project directory (defaults to current directory)
    """
    if project_dir is None:
        project_dir = Path.cwd()

    config_path = project_dir / "uniflow.yaml"

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


# Environment variable helpers


def get_env_config() -> dict[str, Any]:
    """Get configuration from environment variables.

    Returns:
        Dictionary of configuration values from environment
    """
    env_config = {}

    # Map environment variables to config fields
    env_mappings = {
        "UNIFLOW_HOME": "uniflow_home",
        "UNIFLOW_ARTIFACTS_DIR": "artifacts_dir",
        "UNIFLOW_METADATA_DB": "metadata_db",
        "UNIFLOW_CACHE_DIR": "cache_dir",
        "UNIFLOW_DEFAULT_STACK": "default_stack",
        "UNIFLOW_EXECUTION_MODE": "execution_mode",
        "UNIFLOW_REMOTE_SERVER_URL": "remote_server_url",
        "UNIFLOW_REMOTE_UI_URL": "remote_ui_url",
        "UNIFLOW_ENABLE_CACHING": "enable_caching",
        "UNIFLOW_LOG_LEVEL": "log_level",
        "UNIFLOW_UI_HOST": "ui_host",
        "UNIFLOW_UI_PORT": "ui_port",
        "UNIFLOW_DEBUG": "debug_mode",
    }

    for env_var, config_key in env_mappings.items():
        value = os.environ.get(env_var)
        if value is not None:
            # Convert booleans
            if value.lower() in ("true", "1", "yes"):
                value = True
            elif value.lower() in ("false", "0", "no"):
                value = False
            # Convert integers
            elif value.isdigit():
                value = int(value)

            env_config[config_key] = value

    return env_config


def init_config_from_env() -> UniFlowConfig:
    """Initialize configuration from environment variables.

    Returns:
        UniFlowConfig instance with values from environment
    """
    env_config = get_env_config()
    config = UniFlowConfig()

    for key, value in env_config.items():
        if hasattr(config, key):
            setattr(config, key, value)

    return config
