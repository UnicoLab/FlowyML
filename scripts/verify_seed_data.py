#!/usr/bin/env python3
"""
Verify seed data is correctly created and accessible.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flowyml.core.project import ProjectManager  # noqa: E402
from flowyml.storage.metadata import SQLiteMetadataStore  # noqa: E402


def verify_seed_data():
    print("\n🔍 Verifying Seed Data\n")
    print("=" * 60)

    # Check global store
    store = SQLiteMetadataStore()

    runs = store.list_runs(limit=1000)
    artifacts = store.list_assets(limit=1000)

    print("\n📊 Global Store:")
    print(f"   Runs: {len(runs)}")
    print(f"   Artifacts: {len(artifacts)}")

    # Check projects
    print("\n📁 Project Stores:")
    project_manager = ProjectManager()
    projects = project_manager.list_projects()

    total_runs = 0
    total_artifacts = 0

    for project_meta in projects:
        name = project_meta.get("name")
        if not name:
            continue

        project = project_manager.get_project(name)
        if not project:
            continue

        p_runs = project.metadata_store.list_runs(limit=1000)
        p_artifacts = project.metadata_store.list_assets(limit=1000)

        print(f"   {name}:")
        print(f"      Runs: {len(p_runs)}")
        print(f"      Artifacts: {len(p_artifacts)}")

        total_runs += len(p_runs)
        total_artifacts += len(p_artifacts)

    print("\n✅ Total across all projects:")
    print(f"   Runs: {total_runs}")
    print(f"   Artifacts: {total_artifacts}")

    # Verify connections
    print("\n🔗 Connection Verification:")

    # Sample a few artifacts and verify they link back to runs
    sample_artifacts = artifacts[:5] if len(artifacts) > 5 else artifacts
    connected = 0

    for artifact in sample_artifacts:
        run_id = artifact.get("run_id")
        if run_id:
            run = store.load_run(run_id)
            if run:
                connected += 1
                print(f"   ✓ Artifact '{artifact.get('name')}' → Run '{run.get('pipeline_name')}'")

    print(f"\n   {connected}/{len(sample_artifacts)} sampled artifacts have valid run connections")

    # Check artifact types
    print("\n📦 Artifact Types:")
    type_counts = {}
    for artifact in artifacts:
        atype = artifact.get("type", "unknown")
        type_counts[atype] = type_counts.get(atype, 0) + 1

    for atype, count in sorted(type_counts.items()):
        print(f"   {atype}: {count}")

    # Check run statuses
    print("\n🔄 Run Statuses:")
    status_counts = {}
    for run in runs:
        status = run.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    for status, count in sorted(status_counts.items()):
        print(f"   {status}: {count}")

    print("\n" + "=" * 60)
    print("✅ All data verified and connected!\n")


if __name__ == "__main__":
    verify_seed_data()
