"""
Verify API endpoints for UI integration.
"""
import urllib.request
import json
import sys

BASE_URL = "http://localhost:8080/api"


def check(url):
    try:
        print(f"Checking {url}...", end=" ")
        with urllib.request.urlopen(url) as response:
            if response.status == 200:
                print("✅ OK")
                return json.loads(response.read().decode())
            else:
                print(f"❌ Failed ({response.status})")
                return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


print("🔍 Verifying API Endpoints...")

# 1. Experiments
experiments = check(f"{BASE_URL}/experiments")
if experiments and experiments.get("experiments"):
    exp_id = experiments["experiments"][0]["experiment_id"]
    print(f"   Found experiment: {exp_id}")
    check(f"{BASE_URL}/experiments/{exp_id}")
else:
    print("   ⚠️ No experiments found (run test_experiments.py)")

# 2. Runs
runs = check(f"{BASE_URL}/runs")
if runs and runs.get("runs"):
    run_id = runs["runs"][0]["run_id"]
    print(f"   Found run: {run_id}")
    check(f"{BASE_URL}/runs/{run_id}")

    # 3. Artifacts for run
    artifacts = check(f"{BASE_URL}/assets?run_id={run_id}")
    if artifacts and artifacts.get("assets"):
        print(f"   Found {len(artifacts['assets'])} artifacts for run")
        if "artifact_id" not in artifacts["assets"][0]:
            print("   ❌ artifact_id MISSING in response!")
            print(f"   First asset keys: {list(artifacts['assets'][0].keys())}")
        else:
            print("   ✅ artifact_id present in response")
    else:
        print("   ⚠️ No artifacts for this run")

    # 4. Metrics for run
    metrics = check(f"{BASE_URL}/runs/{run_id}/metrics")
    if metrics and metrics.get("metrics"):
        print(f"   Found {len(metrics['metrics'])} metrics for run")
    else:
        print("   ⚠️ No metrics for this run")

print("\n🎉 Verification Complete!")
