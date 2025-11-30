import unittest
import tempfile
import shutil
import os
from pathlib import Path
from flowyml.utils.config import reset_config, update_config, get_config


class BaseTestCase(unittest.TestCase):
    """Base test class for flowyml tests."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)

        # Reset config to defaults
        reset_config()

        # Update config to use temporary directory
        update_config(
            flowyml_home=self.test_path / ".flowyml",
            artifacts_dir=self.test_path / ".flowyml/artifacts",
            metadata_db=self.test_path / ".flowyml/metadata.db",
            cache_dir=self.test_path / ".flowyml/cache",
            runs_dir=self.test_path / ".flowyml/runs",
            experiments_dir=self.test_path / ".flowyml/experiments",
            projects_dir=self.test_path / ".flowyml/projects",
            enable_ui=False,
        )

        # Create directories
        get_config().create_directories()

    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary directory
        shutil.rmtree(self.test_dir)

        # Reset config
        reset_config()
