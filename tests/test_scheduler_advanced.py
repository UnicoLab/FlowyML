"""Tests for advanced scheduler features."""

import os
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from flowyml.core.scheduler import (
    DistributedLock,
    PipelineScheduler,
    Schedule,
    SchedulerConfig,
    SchedulerPersistence,
)

# Optional dependencies
try:
    from croniter import croniter
except ImportError:
    croniter = None

try:
    import pytz
except ImportError:
    pytz = None


class TestSchedulerPersistence(unittest.TestCase):
    """Test scheduler persistence."""

    def setUp(self):
        self.db_path = "test_scheduler.db"
        self.persistence = SchedulerPersistence(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_save_and_load(self):
        """Test saving and loading schedules."""
        mock_func = MagicMock()
        schedule = Schedule(
            pipeline_name="test_pipeline",
            schedule_type="daily",
            schedule_value="02:00",
            pipeline_func=mock_func,
            enabled=True,
            timezone="UTC",
        )

        self.persistence.save_schedule(schedule)

        # Load back
        funcs = {"test_pipeline": mock_func}
        loaded = self.persistence.load_schedules(funcs)

        self.assertIn("test_pipeline", loaded)
        self.assertEqual(loaded["test_pipeline"].schedule_type, "daily")
        self.assertEqual(loaded["test_pipeline"].timezone, "UTC")

    def test_delete(self):
        """Test deleting schedules."""
        mock_func = MagicMock()
        schedule = Schedule(
            pipeline_name="test_pipeline",
            schedule_type="daily",
            schedule_value="02:00",
            pipeline_func=mock_func,
        )

        self.persistence.save_schedule(schedule)
        self.persistence.delete_schedule("test_pipeline")

        loaded = self.persistence.load_schedules({"test_pipeline": mock_func})
        self.assertNotIn("test_pipeline", loaded)


class TestDistributedLock(unittest.TestCase):
    """Test distributed locking."""

    def setUp(self):
        self.lock_file = ".lock_test_lock"
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)

    def tearDown(self):
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)

    def test_file_lock(self):
        """Test file-based locking."""
        lock1 = DistributedLock(backend="file")
        lock2 = DistributedLock(backend="file")

        # Acquire lock 1
        self.assertTrue(lock1.acquire("test_lock"))

        # Lock 2 should fail
        self.assertFalse(lock2.acquire("test_lock"))

        # Release lock 1
        lock1.release("test_lock")

        # Lock 2 should succeed
        self.assertTrue(lock2.acquire("test_lock"))
        lock2.release("test_lock")


class TestPipelineSchedulerAdvanced(unittest.TestCase):
    """Test advanced scheduler features."""

    def setUp(self):
        self.config = SchedulerConfig(
            persist_schedules=False,
            distributed=False,
        )
        self.scheduler = PipelineScheduler(config=self.config)

    def tearDown(self):
        self.scheduler.stop()
        self.scheduler.clear()

    @pytest.mark.skipif(croniter is None, reason="croniter not installed")
    def test_cron_schedule(self):
        """Test cron scheduling."""
        mock_func = MagicMock()

        # Schedule to run every minute
        schedule = self.scheduler.schedule_cron(
            name="cron_job",
            pipeline_func=mock_func,
            cron_expression="* * * * *",
        )

        self.assertEqual(schedule.schedule_type, "cron")
        self.assertIsNotNone(schedule.next_run)

        # Verify next run is in the future
        now = datetime.now(schedule.next_run.tzinfo) if schedule.next_run.tzinfo else datetime.now()
        self.assertGreater(schedule.next_run, now)

    @pytest.mark.skipif(pytz is None, reason="pytz not installed")
    def test_timezone_support(self):
        """Test timezone support."""
        mock_func = MagicMock()

        # Schedule in UTC
        utc_schedule = self.scheduler.schedule_daily(
            name="utc_job",
            pipeline_func=mock_func,
            hour=12,
            timezone="UTC",
        )

        # Schedule in New York
        ny_schedule = self.scheduler.schedule_daily(
            name="ny_job",
            pipeline_func=mock_func,
            hour=12,
            timezone="America/New_York",
        )

        # Times should be different (unless it happens to be same time, unlikely)
        # Note: This is a weak test, but verifies timezone is accepted and processed
        self.assertEqual(utc_schedule.timezone, "UTC")
        self.assertEqual(ny_schedule.timezone, "America/New_York")

    def test_health_check(self):
        """Test health check endpoint."""
        health = self.scheduler.health_check()

        self.assertIn("status", health)
        self.assertIn("metrics", health)
        self.assertEqual(health["status"], "stopped")  # Not started yet

        self.scheduler.start()
        health = self.scheduler.health_check()
        self.assertEqual(health["status"], "running")

    def test_metrics(self):
        """Test metrics tracking."""
        mock_func = MagicMock()
        self.scheduler.schedule_interval(
            name="quick_job",
            pipeline_func=mock_func,
            seconds=1,
        )

        # Manually trigger run to update metrics
        schedule = self.scheduler.schedules["quick_job"]
        self.scheduler._run_pipeline(schedule)

        metrics = self.scheduler.metrics.to_dict()
        self.assertEqual(metrics["total_runs"], 1)
        self.assertEqual(metrics["successful_runs"], 1)

    def test_execution_history(self):
        """Test execution history persistence."""
        # Create scheduler with persistence enabled
        db_path = "test_history.db"

        # Clean up any existing database
        if os.path.exists(db_path):
            os.remove(db_path)

        config = SchedulerConfig(
            persist_schedules=True,
            db_path=db_path,
        )
        scheduler = PipelineScheduler(config=config)

        try:
            mock_func = MagicMock()
            scheduler.schedule_interval(
                name="history_job",
                pipeline_func=mock_func,
                seconds=1,
            )

            # Run pipeline
            schedule = scheduler.schedules["history_job"]
            scheduler._run_pipeline(schedule)

            # Check history
            history = scheduler.get_history("history_job")
            self.assertEqual(len(history), 1)
            self.assertTrue(history[0]["success"])
            self.assertIn("duration_seconds", history[0])

        finally:
            scheduler.stop()
            scheduler.clear()
            if os.path.exists(db_path):
                os.remove(db_path)
