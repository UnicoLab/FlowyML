import unittest
import tempfile
import shutil
import os
from pathlib import Path
from uniflow.utils.config import reset_config, update_config, get_config


class BaseTestCase(unittest.TestCase):
    """Base test class for UniFlow tests."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)

        # Reset config to defaults
        reset_config()

        # Update config to use temporary directory
        update_config(
            uniflow_home=self.test_path / ".uniflow",
            artifacts_dir=self.test_path / ".uniflow/artifacts",
            metadata_db=self.test_path / ".uniflow/metadata.db",
            cache_dir=self.test_path / ".uniflow/cache",
            runs_dir=self.test_path / ".uniflow/runs",
            experiments_dir=self.test_path / ".uniflow/experiments",
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
