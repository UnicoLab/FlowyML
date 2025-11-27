"""Tests for uniflow.utils.environment."""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from pathlib import Path
from uniflow.utils.environment import (
    get_python_info,
    get_system_info,
    get_installed_packages,
    get_key_packages,
    get_environment_variables,
    get_working_directory,
    capture_environment,
    detect_environment_type,
)


class TestEnvironmentUtils(unittest.TestCase):
    """Test environment utility functions."""

    def test_get_python_info(self):
        """Test getting Python info."""
        info = get_python_info()
        self.assertIn("version", info)
        self.assertIn("version_info", info)
        self.assertIn("implementation", info)
        self.assertIn("compiler", info)
        self.assertIn("executable", info)

    @patch("platform.platform")
    @patch("platform.system")
    def test_get_system_info(self, mock_system, mock_platform):
        """Test getting system info."""
        mock_platform.return_value = "Test Platform"
        mock_system.return_value = "Test System"

        info = get_system_info()
        self.assertEqual(info["platform"], "Test Platform")
        self.assertEqual(info["system"], "Test System")
        self.assertIn("hostname", info)

    @patch("pkg_resources.working_set")
    def test_get_installed_packages(self, mock_working_set):
        """Test getting installed packages."""
        # Mock pkg_resources
        dist1 = MagicMock()
        dist1.project_name = "package1"
        dist1.version = "1.0.0"

        dist2 = MagicMock()
        dist2.project_name = "package2"
        dist2.version = "2.0.0"

        mock_working_set.__iter__.return_value = [dist1, dist2]

        packages = get_installed_packages()
        self.assertEqual(packages["package1"], "1.0.0")
        self.assertEqual(packages["package2"], "2.0.0")

    def test_get_key_packages(self):
        """Test getting key packages."""
        with patch("uniflow.utils.environment.get_installed_packages") as mock_get:
            mock_get.return_value = {
                "numpy": "1.21.0",
                "pandas": "1.3.0",
                "other_pkg": "0.1.0",
            }

            key_pkgs = get_key_packages()
            self.assertIn("numpy", key_pkgs)
            self.assertIn("pandas", key_pkgs)
            self.assertNotIn("other_pkg", key_pkgs)

    def test_get_environment_variables(self):
        """Test getting environment variables."""
        with patch.dict(os.environ, {"PYTHONPATH": "/test/path", "SECRET": "hidden"}):
            # Safe vars only
            env_vars = get_environment_variables(include_all=False)
            self.assertIn("PYTHONPATH", env_vars)
            self.assertNotIn("SECRET", env_vars)

            # All vars
            all_vars = get_environment_variables(include_all=True)
            self.assertIn("PYTHONPATH", all_vars)
            self.assertIn("SECRET", all_vars)

    def test_get_working_directory(self):
        """Test getting working directory."""
        cwd = get_working_directory()
        self.assertEqual(cwd, str(Path.cwd()))

    @patch("uniflow.utils.git.get_git_info")
    def test_capture_environment(self, mock_get_git):
        """Test capturing complete environment."""
        mock_git_info = MagicMock()
        mock_git_info.is_available = True
        mock_git_info.to_dict.return_value = {"commit": "abc"}
        mock_get_git.return_value = mock_git_info

        env = capture_environment(include_git=True)

        self.assertIn("python", env)
        self.assertIn("system", env)
        self.assertIn("key_packages", env)
        self.assertIn("git", env)
        self.assertEqual(env["git"]["commit"], "abc")

    def test_detect_environment_type(self):
        """Test environment detection."""
        # Local
        with patch.dict(os.environ, {}, clear=True):
            with patch("pathlib.Path.exists", return_value=False):
                self.assertEqual(detect_environment_type(), "local")

        # Docker
        with patch("pathlib.Path.exists", return_value=True):
            self.assertEqual(detect_environment_type(), "docker")

        # Kubernetes
        with patch.dict(os.environ, {"KUBERNETES_SERVICE_HOST": "10.0.0.1"}):
            with patch("pathlib.Path.exists", return_value=False):
                self.assertEqual(detect_environment_type(), "kubernetes")
