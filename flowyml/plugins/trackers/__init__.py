"""FlowyML Trackers Plugins."""

# Import trackers as they are implemented
# This allows: from flowyml.plugins.trackers import MLflowTracker

try:
    from flowyml.plugins.trackers.mlflow import MLflowTracker
except ImportError:
    MLflowTracker = None  # MLflow not installed

__all__ = ["MLflowTracker"]
