import unittest
from unittest.mock import MagicMock, patch
import time
import threading
from flowyml import Pipeline, step
from flowyml.core.executor import LocalExecutor, StopExecution, MonitorThread, HeartbeatThread


class TestHeartbeatIntegration(unittest.TestCase):
    def test_heartbeat_thread_sends_requests(self):
        """Test that MonitorThread sends requests to the API."""
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"action": "continue"}

            thread = MonitorThread(
                run_id="test_run",
                step_name="test_step",
                target_tid=threading.get_ident(),
                interval=0.1,
            )
            thread.start()
            time.sleep(0.3)
            thread.stop()
            thread.join()

            self.assertTrue(mock_post.called)
            self.assertGreaterEqual(mock_post.call_count, 1)

    def test_heartbeat_stops_execution(self):
        """Test that MonitorThread raises StopExecution when receiving stop signal."""
        # We need to run this in a separate thread because it raises an exception in the target thread

        execution_stopped = threading.Event()

        def target_function():
            try:
                # Simulate long running task
                for _ in range(10):
                    time.sleep(0.1)
            except StopExecution:
                execution_stopped.set()

        target_thread = threading.Thread(target=target_function)
        target_thread.start()

        # Give it time to start
        time.sleep(0.1)

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"action": "stop"}

            heartbeat = MonitorThread(
                run_id="test_run",
                step_name="test_step",
                target_tid=target_thread.ident,
                interval=0.1,
            )
            heartbeat.start()

            # Wait for stop signal to be processed
            target_thread.join(timeout=2)
            heartbeat.stop()
            heartbeat.join()

            self.assertTrue(execution_stopped.is_set(), "StopExecution exception was not raised in target thread")

    def test_executor_handles_stop_execution(self):
        """Test that LocalExecutor handles StopExecution exception correctly."""

        @step
        def long_step():
            time.sleep(1)
            return "done"

        pipeline = Pipeline("test_pipeline", enable_cache=False)
        pipeline.add_step(long_step)

        # Let's try testing the executor with the real MonitorThread but mocked API
        with patch("requests.post") as mock_post:
            # Configure mock responses
            resp_continue = MagicMock()
            resp_continue.status_code = 200
            resp_continue.json.return_value = {"action": "continue"}

            resp_stop = MagicMock()
            resp_stop.status_code = 200
            resp_stop.json.return_value = {"action": "stop"}

            # First response continues, subsequent ones stop
            mock_post.side_effect = [resp_continue] + [resp_stop] * 20

            # Use a very short interval for testing by patching MonitorThread
            original_init = MonitorThread.__init__

            def patched_init(self, *args, **kwargs):
                kwargs["interval"] = 0.1
                return original_init(self, *args, **kwargs)

            with patch.object(MonitorThread, "__init__", patched_init):
                result = pipeline.run()

                self.assertFalse(result.success)
                self.assertIn("stopped by user", result.step_results["long_step"].error)


if __name__ == "__main__":
    unittest.main()
