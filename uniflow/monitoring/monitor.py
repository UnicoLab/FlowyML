from uniflow.monitoring.alerts import alert_manager, AlertLevel


class Monitor:
    """Base class for monitors."""

    def __init__(self, name: str):
        self.name = name

    def check(self) -> bool:
        """Perform check. Return True if healthy."""
        raise NotImplementedError


class SystemMonitor(Monitor):
    """Monitors system resources."""

    def check(self) -> bool:
        try:
            import psutil
        except ImportError:
            return True  # Skip if psutil not installed

        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent

        if cpu > 90:
            alert_manager.send_alert(
                "High CPU Usage",
                f"CPU usage is at {cpu}%",
                AlertLevel.WARNING,
            )
            return False

        if mem > 90:
            alert_manager.send_alert(
                "High Memory Usage",
                f"Memory usage is at {mem}%",
                AlertLevel.WARNING,
            )
            return False

        return True


class PipelineMonitor(Monitor):
    """Monitors pipeline execution health."""

    def __init__(self, pipeline_name: str):
        super().__init__(f"pipeline-{pipeline_name}")
        self.pipeline_name = pipeline_name
        self.failed_runs_threshold = 3

    def check(self) -> bool:
        # Logic to check recent runs from metadata store
        # For now, placeholder
        return True
