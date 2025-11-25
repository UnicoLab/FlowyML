"""Metadata storage backends for Flowy."""

import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class MetadataStore(ABC):
    """Base class for metadata storage backends."""

    @abstractmethod
    def save_run(self, run_id: str, metadata: dict) -> None:
        """Save run metadata."""
        pass

    @abstractmethod
    def load_run(self, run_id: str) -> Optional[dict]:
        """Load run metadata."""
        pass

    @abstractmethod
    def list_runs(self, limit: Optional[int] = None) -> list[dict]:
        """List all runs."""
        pass

    @abstractmethod
    def list_pipelines(self) -> list[str]:
        """List all unique pipeline names."""
        pass

    @abstractmethod
    def save_artifact(self, artifact_id: str, metadata: dict) -> None:
        """Save artifact metadata."""
        pass

    @abstractmethod
    def load_artifact(self, artifact_id: str) -> Optional[dict]:
        """Load artifact metadata."""
        pass

    @abstractmethod
    def list_assets(self, limit: Optional[int] = None, **filters) -> list[dict]:
        """List assets with optional filters."""
        pass

    @abstractmethod
    def query(self, **filters) -> list[dict]:
        """Query runs with filters."""
        pass


class SQLiteMetadataStore(MetadataStore):
    """SQLite-based metadata storage."""

    def __init__(self, db_path: str = ".flowy/metadata.db"):
        """Initialize SQLite metadata store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                pipeline_name TEXT,
                status TEXT,
                start_time TEXT,
                end_time TEXT,
                duration REAL,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Artifacts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS artifacts (
                artifact_id TEXT PRIMARY KEY,
                name TEXT,
                type TEXT,
                run_id TEXT,
                path TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)

        # Metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                name TEXT,
                value REAL,
                step INTEGER,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)

        # Parameters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parameters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                name TEXT,
                value TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)

        # Experiments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Experiment Runs link table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiment_runs (
                experiment_id TEXT,
                run_id TEXT,
                metrics TEXT,
                parameters TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (experiment_id, run_id),
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id),
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)

        # Create indexes for better query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_pipeline ON runs(pipeline_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_run ON artifacts(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_run ON metrics(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parameters_run ON parameters(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_experiments_name ON experiments(name)")

        conn.commit()
        conn.close()

    def save_run(self, run_id: str, metadata: dict) -> None:
        """Save run metadata to database.

        Args:
            run_id: Unique run identifier
            metadata: Run metadata dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO runs
            (run_id, pipeline_name, status, start_time, end_time, duration, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            metadata.get('pipeline_name'),
            metadata.get('status'),
            metadata.get('start_time'),
            metadata.get('end_time'),
            metadata.get('duration'),
            json.dumps(metadata)
        ))

        # Save parameters
        if 'parameters' in metadata:
            cursor.execute("DELETE FROM parameters WHERE run_id = ?", (run_id,))
            for name, value in metadata['parameters'].items():
                cursor.execute(
                    "INSERT INTO parameters (run_id, name, value) VALUES (?, ?, ?)",
                    (run_id, name, json.dumps(value))
                )

        # Save metrics
        if 'metrics' in metadata:
            cursor.execute("DELETE FROM metrics WHERE run_id = ?", (run_id,))
            for name, value in metadata['metrics'].items():
                cursor.execute(
                    "INSERT INTO metrics (run_id, name, value, step) VALUES (?, ?, ?, ?)",
                    (run_id, name, value, 0)
                )

        conn.commit()
        conn.close()

    def load_run(self, run_id: str) -> Optional[dict]:
        """Load run metadata from database.

        Args:
            run_id: Unique run identifier

        Returns:
            Run metadata dictionary or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT metadata FROM runs WHERE run_id = ?", (run_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            return json.loads(row[0])
        return None

    def list_runs(self, limit: Optional[int] = None) -> list[dict]:
        """List all runs from database.

        Args:
            limit: Optional limit on number of results

        Returns:
            List of run metadata dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT metadata FROM runs ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        rows = cursor.fetchall()

        conn.close()

        return [json.loads(row[0]) for row in rows]

    def list_pipelines(self) -> list[str]:
        """List all unique pipeline names.

        Returns:
            List of pipeline names
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT pipeline_name FROM runs ORDER BY pipeline_name")
        rows = cursor.fetchall()

        conn.close()

        return [row[0] for row in rows if row[0]]

    def save_artifact(self, artifact_id: str, metadata: dict) -> None:
        """Save artifact metadata to database.

        Args:
            artifact_id: Unique artifact identifier
            metadata: Artifact metadata dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO artifacts
            (artifact_id, name, type, run_id, path, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            artifact_id,
            metadata.get('name'),
            metadata.get('type'),
            metadata.get('run_id'),
            metadata.get('path'),
            json.dumps(metadata)
        ))

        conn.commit()
        conn.close()

    def load_artifact(self, artifact_id: str) -> Optional[dict]:
        """Load artifact metadata from database.

        Args:
            artifact_id: Unique artifact identifier

        Returns:
            Artifact metadata dictionary or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT metadata FROM artifacts WHERE artifact_id = ?", (artifact_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            return json.loads(row[0])
        return None

    def list_assets(self, limit: Optional[int] = None, **filters) -> list[dict]:
        """List assets from database with optional filters.

        Args:
            limit: Optional limit on number of results
            **filters: Filter criteria (type, run_id, etc.)

        Returns:
            List of artifact metadata dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        conditions = []
        params = []

        for key, value in filters.items():
            if value is not None:
                conditions.append(f"{key} = ?")
                params.append(value)

        query = "SELECT metadata FROM artifacts"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        conn.close()

        return [json.loads(row[0]) for row in rows]

    def query(self, **filters) -> list[dict]:
        """Query runs with filters.

        Args:
            **filters: Filter criteria (pipeline_name, status, etc.)

        Returns:
            List of matching run metadata dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        where_clauses = []
        params = []

        for key, value in filters.items():
            where_clauses.append(f"{key} = ?")
            params.append(value)

        query = "SELECT metadata FROM runs"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        query += " ORDER BY created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        conn.close()

        return [json.loads(row[0]) for row in rows]

    def save_metric(self, run_id: str, name: str, value: float, step: int = 0) -> None:
        """Save a single metric value.

        Args:
            run_id: Run identifier
            name: Metric name
            value: Metric value
            step: Training step/iteration
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO metrics (run_id, name, value, step) VALUES (?, ?, ?, ?)",
            (run_id, name, value, step)
        )

        conn.commit()
        conn.close()

    def get_metrics(self, run_id: str, name: Optional[str] = None) -> list[dict]:
        """Get metrics for a run.

        Args:
            run_id: Run identifier
            name: Optional metric name filter

        Returns:
            List of metric dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if name:
            cursor.execute(
                "SELECT name, value, step, timestamp FROM metrics WHERE run_id = ? AND name = ? ORDER BY step",
                (run_id, name)
            )
        else:
            cursor.execute(
                "SELECT name, value, step, timestamp FROM metrics WHERE run_id = ? ORDER BY step",
                (run_id,)
            )

        rows = cursor.fetchall()
        conn.close()

        return [
            {'name': row[0], 'value': row[1], 'step': row[2], 'timestamp': row[3]}
            for row in rows
        ]
        
    def save_experiment(self, experiment_id: str, name: str, description: str = "", tags: dict = None) -> None:
        """Save experiment metadata.
        
        Args:
            experiment_id: Unique experiment identifier
            name: Experiment name
            description: Experiment description
            tags: Experiment tags
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO experiments
            (experiment_id, name, description, tags)
            VALUES (?, ?, ?, ?)
        """, (
            experiment_id,
            name,
            description,
            json.dumps(tags or {})
        ))
        
        conn.commit()
        conn.close()
        
    def log_experiment_run(self, experiment_id: str, run_id: str, metrics: dict = None, parameters: dict = None) -> None:
        """Log a run to an experiment.
        
        Args:
            experiment_id: Experiment identifier
            run_id: Run identifier
            metrics: Metrics from the run
            parameters: Parameters used in the run
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO experiment_runs
            (experiment_id, run_id, metrics, parameters)
            VALUES (?, ?, ?, ?)
        """, (
            experiment_id,
            run_id,
            json.dumps(metrics or {}),
            json.dumps(parameters or {})
        ))
        
        conn.commit()
        conn.close()
        
    def list_experiments(self) -> list[dict]:
        """List all experiments.
        
        Returns:
            List of experiment dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT experiment_id, name, description, tags, created_at FROM experiments ORDER BY created_at DESC")
        rows = cursor.fetchall()
        
        experiments = []
        for row in rows:
            # Count runs for each experiment
            cursor.execute("SELECT COUNT(*) FROM experiment_runs WHERE experiment_id = ?", (row[0],))
            run_count = cursor.fetchone()[0]
            
            experiments.append({
                'experiment_id': row[0],
                'name': row[1],
                'description': row[2],
                'tags': json.loads(row[3]),
                'created_at': row[4],
                'run_count': run_count
            })
            
        conn.close()
        return experiments
        
    def get_experiment(self, experiment_id: str) -> Optional[dict]:
        """Get experiment details.
        
        Args:
            experiment_id: Experiment identifier
            
        Returns:
            Experiment dictionary or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT experiment_id, name, description, tags, created_at FROM experiments WHERE experiment_id = ?", (experiment_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
            
        experiment = {
            'experiment_id': row[0],
            'name': row[1],
            'description': row[2],
            'tags': json.loads(row[3]),
            'created_at': row[4]
        }
        
        # Get runs
        cursor.execute("""
            SELECT er.run_id, er.metrics, er.parameters, er.timestamp, r.status, r.duration
            FROM experiment_runs er
            LEFT JOIN runs r ON er.run_id = r.run_id
            WHERE er.experiment_id = ?
            ORDER BY er.timestamp DESC
        """, (experiment_id,))
        
        runs = []
        for r in cursor.fetchall():
            runs.append({
                'run_id': r[0],
                'metrics': json.loads(r[1]),
                'parameters': json.loads(r[2]),
                'timestamp': r[3],
                'status': r[4],
                'duration': r[5]
            })
            
        experiment['runs'] = runs
        
        conn.close()
        return experiment

    def get_statistics(self) -> dict:
        """Get database statistics.

        Returns:
            Dictionary with statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {}

        cursor.execute("SELECT COUNT(*) FROM runs")
        stats['total_runs'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM artifacts")
        stats['total_artifacts'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM metrics")
        stats['total_metrics'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT pipeline_name) FROM runs")
        stats['total_pipelines'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM experiments")
        stats['total_experiments'] = cursor.fetchone()[0]

        conn.close()

        return stats

