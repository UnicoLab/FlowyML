"""
Tests for scheduling functionality.
"""

import unittest
import time
import threading
from datetime import datetime, timedelta
from uniflow.core.scheduler import PipelineScheduler, Schedule

class TestPipelineScheduler(unittest.TestCase):
    
    def setUp(self):
        self.scheduler = PipelineScheduler()
        self.execution_count = 0
        
    def tearDown(self):
        if self.scheduler.running:
            self.scheduler.stop()
            
    def sample_pipeline(self):
        """Sample pipeline function."""
        self.execution_count += 1
        return {"status": "success"}
        
    def test_schedule_daily(self):
        """Test daily scheduling."""
        schedule = self.scheduler.schedule_daily(
            name="test_daily",
            pipeline_func=self.sample_pipeline,
            hour=10,
            minute=30
        )
        
        self.assertEqual(schedule.schedule_type, 'daily')
        self.assertEqual(schedule.schedule_value, '10:30')
        self.assertTrue(schedule.enabled)
        self.assertIsNotNone(schedule.next_run)
        
    def test_schedule_interval(self):
        """Test interval scheduling."""
        schedule = self.scheduler.schedule_interval(
            name="test_interval",
            pipeline_func=self.sample_pipeline,
            hours=1,
            minutes=30
        )
        
        self.assertEqual(schedule.schedule_type, 'interval')
        self.assertEqual(schedule.schedule_value, str(90 * 60))  # 5400 seconds
        self.assertIsNotNone(schedule.next_run)
        
    def test_schedule_hourly(self):
        """Test hourly scheduling."""
        schedule = self.scheduler.schedule_hourly(
            name="test_hourly",
            pipeline_func=self.sample_pipeline,
            minute=15
        )
        
        self.assertEqual(schedule.schedule_type, 'hourly')
        self.assertEqual(schedule.schedule_value, '15')
        
    def test_unschedule(self):
        """Test removing a schedule."""
        self.scheduler.schedule_daily(
            name="test_remove",
            pipeline_func=self.sample_pipeline
        )
        
        self.assertIn("test_remove", self.scheduler.schedules)
        self.scheduler.unschedule("test_remove")
        self.assertNotIn("test_remove", self.scheduler.schedules)
        
    def test_enable_disable(self):
        """Test enabling/disabling schedules."""
        self.scheduler.schedule_daily(
            name="test_toggle",
            pipeline_func=self.sample_pipeline
        )
        
        self.assertTrue(self.scheduler.schedules["test_toggle"].enabled)
        
        self.scheduler.disable("test_toggle")
        self.assertFalse(self.scheduler.schedules["test_toggle"].enabled)
        
        self.scheduler.enable("test_toggle")
        self.assertTrue(self.scheduler.schedules["test_toggle"].enabled)
        
    def test_scheduler_start_stop(self):
        """Test starting and stopping the scheduler."""
        self.assertFalse(self.scheduler.running)
        
        self.scheduler.start()
        time.sleep(0.1)  # Give it time to start
        self.assertTrue(self.scheduler.running)
        
        self.scheduler.stop()
        self.assertFalse(self.scheduler.running)
        
    def test_list_schedules(self):
        """Test listing schedules."""
        self.scheduler.schedule_daily("daily_1", self.sample_pipeline)
        self.scheduler.schedule_hourly("hourly_1", self.sample_pipeline)
        
        schedules = self.scheduler.list_schedules()
        self.assertEqual(len(schedules), 2)

if __name__ == '__main__':
    unittest.main()
