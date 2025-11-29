"""Tests for flowyml.utils.git."""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from flowyml.utils.git import (
    run_git_command,
    is_git_repo,
    get_commit_hash,
    get_branch_name,
    is_dirty,
    get_git_info,
    GitInfo,
)


class TestGitUtils(unittest.TestCase):
    """Test git utility functions."""

    @patch("subprocess.run")
    def test_run_git_command(self, mock_run):
        """Test running git command."""
        # Success case
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "output\n"
        mock_run.return_value = mock_result

        output = run_git_command(["status"])
        self.assertEqual(output, "output")

        # Failure case
        mock_result.returncode = 1
        output = run_git_command(["status"])
        self.assertIsNone(output)

    @patch("flowyml.utils.git.run_git_command")
    def test_is_git_repo(self, mock_run):
        """Test checking if directory is git repo."""
        mock_run.return_value = ".git"
        self.assertTrue(is_git_repo())

        mock_run.return_value = None
        self.assertFalse(is_git_repo())

    @patch("flowyml.utils.git.run_git_command")
    def test_get_commit_hash(self, mock_run):
        """Test getting commit hash."""
        mock_run.return_value = "abcdef123456"
        self.assertEqual(get_commit_hash(), "abcdef123456")

    @patch("flowyml.utils.git.run_git_command")
    def test_get_branch_name(self, mock_run):
        """Test getting branch name."""
        mock_run.return_value = "main"
        self.assertEqual(get_branch_name(), "main")

    @patch("flowyml.utils.git.run_git_command")
    def test_is_dirty(self, mock_run):
        """Test checking if repo is dirty."""
        mock_run.return_value = "M file.py"
        self.assertTrue(is_dirty())

        mock_run.return_value = ""
        self.assertFalse(is_dirty())

        mock_run.return_value = None
        self.assertFalse(is_dirty())

    @patch("flowyml.utils.git.is_git_repo")
    @patch("flowyml.utils.git.get_commit_hash")
    @patch("flowyml.utils.git.get_branch_name")
    def test_get_git_info(self, mock_branch, mock_hash, mock_is_repo):
        """Test getting full git info."""
        mock_is_repo.return_value = True
        mock_hash.return_value = "abc"
        mock_branch.return_value = "main"

        info = get_git_info()
        self.assertIsInstance(info, GitInfo)
        self.assertEqual(info.commit_hash, "abc")
        self.assertEqual(info.branch, "main")
        self.assertTrue(info.is_available)

        # Not a repo
        mock_is_repo.return_value = False
        info = get_git_info()
        self.assertFalse(info.is_available)
