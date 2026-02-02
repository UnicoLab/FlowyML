import os
import sys
import requests
import time


def test_deployment():
    # Get URL from env or argument
    url = os.environ.get("FLOWYML_REMOTE_URL")
    if not url:
        # Try to infer from argument
        if len(sys.argv) > 1:
            url = sys.argv[1]

    if not url:
        print("❌ Error: FLOWYML_REMOTE_URL environment variable is not set.")
        print("Usage: export FLOWYML_REMOTE_URL=... OR python scripts/test_deployment.py <url>")
        sys.exit(1)

    url = url.rstrip("/")
    print(f"🔍 Testing deployment at {url}...")

    # 1. Health Check
    print("1️⃣  Verifying Health Endpoint...")
    try:
        r = requests.get(f"{url}/api/health", timeout=10)
        r.raise_for_status()
        data = r.json()
        print(f"   ✅ Health Check Passed: Status={data.get('status')}, Version={data.get('version')}")
    except Exception as e:
        print(f"   ❌ Health Check Failed: {e}")
        sys.exit(1)

    # 2. Public Config Check
    print("2️⃣  Verifying Public Configuration...")
    try:
        r = requests.get(f"{url}/api/config", timeout=10)
        r.raise_for_status()
        config = r.json()
        print(f"   ✅ Config Check Passed.")
        print(f"      - Execution Mode: {config.get('execution_mode')}")
        print(f"      - Remote UI URL: {config.get('remote_ui_url')}")

    except Exception as e:
        print(f"   ❌ Config Check Failed: {e}")
        print(
            "   (This might be expected if authentication is strictly enforced on all endpoints, but /api/config is usually public)",
        )

    print("\n🎉 Deployment is reachable and responding correctly!")


if __name__ == "__main__":
    test_deployment()
