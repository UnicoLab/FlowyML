"""Environment capture utilities for reproducibility."""

import sys
import platform
import os
from pathlib import Path
from typing import Any
from datetime import datetime


def get_python_info() -> dict[str, str]:
    """Get Python version and implementation info.

    Returns:
        Dictionary with Python information
    """
    return {
        "version": sys.version,
        "version_info": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "implementation": platform.python_implementation(),
        "compiler": platform.python_compiler(),
        "executable": sys.executable,
    }


def get_system_info() -> dict[str, str]:
    """Get system and hardware information.

    Returns:
        Dictionary with system information
    """
    info = {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node(),
    }

    # Add CPU count if available
    try:
        import multiprocessing

        info["cpu_count"] = str(multiprocessing.cpu_count())
    except Exception:
        pass

    # Add GPU info if available
    try:
        import torch

        if torch.cuda.is_available():
            info["cuda_available"] = "true"
            info["cuda_version"] = torch.version.cuda
            info["gpu_count"] = str(torch.cuda.device_count())
            info["gpu_name"] = torch.cuda.get_device_name(0)
        else:
            info["cuda_available"] = "false"
    except ImportError:
        pass

    return info


def get_installed_packages() -> dict[str, str]:
    """Get list of installed packages and versions.

    Returns:
        Dictionary mapping package names to versions
    """
    packages = {}

    try:
        import pkg_resources

        for dist in pkg_resources.working_set:
            packages[dist.project_name] = dist.version
    except Exception:
        pass

    # Alternative method using importlib.metadata (Python 3.8+)
    if not packages:
        try:
            from importlib import metadata

            for dist in metadata.distributions():
                packages[dist.name] = dist.version
        except Exception:
            pass

    return packages


def get_key_packages() -> dict[str, str]:
    """Get versions of key ML/data packages.

    Returns:
        Dictionary with key package versions
    """
    key_packages = [
        "numpy",
        "pandas",
        "torch",
        "tensorflow",
        "scikit-learn",
        "transformers",
        "pydantic",
        "uniflow",
    ]

    versions = {}
    all_packages = get_installed_packages()

    for pkg in key_packages:
        if pkg in all_packages:
            versions[pkg] = all_packages[pkg]

    return versions


def get_environment_variables(include_all: bool = False) -> dict[str, str]:
    """Get relevant environment variables.

    Args:
        include_all: Include all environment variables (may contain secrets!)

    Returns:
        Dictionary of environment variables
    """
    if include_all:
        return dict(os.environ)

    # Only include safe, ML-relevant environment variables
    safe_vars = [
        "CUDA_VISIBLE_DEVICES",
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "PYTHONPATH",
        "PATH",
        "HOME",
        "USER",
        "SHELL",
        "TERM",
    ]

    env_vars = {}
    for var in safe_vars:
        if var in os.environ:
            env_vars[var] = os.environ[var]

    return env_vars


def get_working_directory() -> str:
    """Get current working directory.

    Returns:
        Working directory path
    """
    return str(Path.cwd())


def capture_environment(
    include_packages: bool = True,
    include_git: bool = True,
    include_system: bool = True,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Capture complete environment information.

    Args:
        include_packages: Include installed packages
        include_git: Include git information (from project root only)
        include_system: Include system information
        project_root: Project root directory (for git tracking)

    Returns:
        Dictionary with environment information
    """
    env_info = {
        "captured_at": datetime.now().isoformat(),
        "python": get_python_info(),
        "working_directory": get_working_directory(),
    }

    if include_system:
        env_info["system"] = get_system_info()

    if include_packages:
        env_info["key_packages"] = get_key_packages()

    if include_git:
        # Only get git info from the project directory (not UniFlow's directory)
        from uniflow.utils.git import get_git_info

        git_path = project_root or Path.cwd()
        git_info = get_git_info(git_path)

        if git_info.is_available:
            env_info["git"] = git_info.to_dict()

    env_info["environment_variables"] = get_environment_variables()

    return env_info


def save_environment(
    output_path: Path,
    include_packages: bool = True,
    include_git: bool = True,
    include_system: bool = True,
    project_root: Path | None = None,
) -> None:
    """Save environment information to file.

    Args:
        output_path: Path to save environment info
        include_packages: Include installed packages
        include_git: Include git information
        include_system: Include system information
        project_root: Project root directory
    """
    import json

    env_info = capture_environment(
        include_packages=include_packages,
        include_git=include_git,
        include_system=include_system,
        project_root=project_root,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(env_info, f, indent=2)


def export_requirements(output_path: Path, export_format: str = "pip") -> None:
    """Export installed packages to requirements file.

    Args:
        output_path: Path to save requirements
        export_format: Format (pip, conda, poetry)
    """
    packages = get_installed_packages()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if export_format == "pip":
        with open(output_path, "w") as f:
            for name, version in sorted(packages.items()):
                f.write(f"{name}=={version}\n")

    elif export_format == "conda":
        with open(output_path, "w") as f:
            f.write("name: uniflow-env\n")
            f.write("channels:\n")
            f.write("  - defaults\n")
            f.write("  - conda-forge\n")
            f.write("dependencies:\n")
            for name, version in sorted(packages.items()):
                f.write(f"  - {name}=={version}\n")

    elif export_format == "poetry":
        with open(output_path, "w") as f:
            f.write("[tool.poetry.dependencies]\n")
            f.write(f'python = "^{sys.version_info.major}.{sys.version_info.minor}"\n')
            for name, version in sorted(packages.items()):
                if name != "python":
                    f.write(f'{name} = "^{version}"\n')


def compare_environments(env1: dict[str, Any], env2: dict[str, Any]) -> dict[str, Any]:
    """Compare two environment captures.

    Args:
        env1: First environment
        env2: Second environment

    Returns:
        Dictionary with differences
    """
    differences = {}

    # Compare Python versions
    if env1.get("python", {}).get("version_info") != env2.get("python", {}).get("version_info"):
        differences["python_version"] = {
            "env1": env1.get("python", {}).get("version_info"),
            "env2": env2.get("python", {}).get("version_info"),
        }

    # Compare packages
    packages1 = set(env1.get("key_packages", {}).items())
    packages2 = set(env2.get("key_packages", {}).items())

    if packages1 != packages2:
        differences["package_differences"] = {
            "only_in_env1": dict(packages1 - packages2),
            "only_in_env2": dict(packages2 - packages1),
        }

    # Compare git info
    git1 = env1.get("git", {})
    git2 = env2.get("git", {})

    if git1.get("commit_hash") != git2.get("commit_hash"):
        differences["git_commit"] = {
            "env1": git1.get("commit_hash"),
            "env2": git2.get("commit_hash"),
        }

    return differences


def detect_environment_type() -> str:
    """Detect the type of environment (local, docker, cloud, etc.).

    Returns:
        Environment type string
    """
    # Check for Docker
    if Path("/.dockerenv").exists():
        return "docker"

    # Check for cloud environments
    if "KUBERNETES_SERVICE_HOST" in os.environ:
        return "kubernetes"

    if "AWS_EXECUTION_ENV" in os.environ:
        return "aws_lambda"

    if "GOOGLE_CLOUD_PROJECT" in os.environ:
        return "gcp"

    if "AZURE_FUNCTIONS_ENVIRONMENT" in os.environ:
        return "azure_functions"

    # Check for notebooks
    try:
        get_ipython()  # type: ignore
        return "jupyter"
    except NameError:
        pass

    return "local"
