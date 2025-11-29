"""Verification script for Airflow integration via GenericBridge."""

import sys
from unittest.mock import MagicMock

from flowyml.stacks.components import Orchestrator
from flowyml.stacks.plugins import get_component_registry

# Mock Airflow modules
mock_airflow = MagicMock()
mock_bq = MagicMock()


class BigQueryExecuteQueryOperator:
    def __init__(self, **kwargs):
        self.params = kwargs

    def execute(self, context, **kwargs):
        print(f"🌪️ [Airflow BQ] Executing query with params {self.params}")
        return "job_id_456"


mock_bq.BigQueryExecuteQueryOperator = BigQueryExecuteQueryOperator

sys.modules["airflow"] = mock_airflow
sys.modules["airflow.providers.google.cloud.operators.bigquery"] = mock_bq


def verify_airflow_integration():
    print("🔌 Loading Airflow plugins from config...")
    registry = get_component_registry()
    registry.load_plugins_from_config("examples/plugins/airflow_config.yaml")

    # Verify Operator as Orchestrator (Generic mapping)
    print("\n✅ Verifying Airflow Operator...")
    bq_cls = registry.get_orchestrator("airflow_bigquery")
    if bq_cls:
        # In Airflow, we pass params. Here we pass them as kwargs which our wrapper handles
        op = bq_cls(sql="SELECT * FROM table")
        if not isinstance(op, Orchestrator):
            msg = "Operator is not an Orchestrator instance"
            raise TypeError(msg)
        print(f"   Loaded: {op.name}")

        # 'run_pipeline' is mapped to 'execute'
        op.run_pipeline({"execution_date": "2023-01-01"})
    else:
        print("❌ Failed to load Airflow operator")


if __name__ == "__main__":
    verify_airflow_integration()
