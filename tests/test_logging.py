"""Test suite for logging functionality."""

import unittest
import logging
from flowyml.utils.logging import get_logger, setup_logger


class TestLogging(unittest.TestCase):
    """Test suite for logging functionality."""

    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger("test_module")
        self.assertIsInstance(logger, logging.Logger)

    def test_get_logger_default(self):
        """Test getting logger with default name."""
        logger = get_logger()
        self.assertIsInstance(logger, logging.Logger)

    def test_setup_logger(self):
        """Test setting up a logger."""
        logger = setup_logger(name="custom_logger", level=logging.INFO)
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.level, logging.INFO)

    def test_setup_logger_debug(self):
        """Test setting up debug logger."""
        logger = setup_logger(name="debug_logger", level=logging.DEBUG)
        self.assertEqual(logger.level, logging.DEBUG)


if __name__ == "__main__":
    unittest.main()
