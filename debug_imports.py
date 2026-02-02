import sys

modules = [
    "inspect",
    "typing",
    "abc",
    "collections",
    "contextlib",
    "copy",
    "dataclasses",
    "datetime",
    "enum",
    "functools",
    "importlib",
    "json",
    "logging",
    "math",
    "pathlib",
    "random",
    "re",
    "shutil",
    "subprocess",
    "tempfile",
    "threading",
    "time",
    "traceback",
    "uuid",
    "warnings",
    # External
    "rich",
    "numpy",
    "pandas",
    "fastapi",
    "uvicorn",
    "requests",
    "pydantic",
    "yaml",
    "psutil",
]

for m in modules:
    try:
        print(f"Importing {m}...", flush=True)
        __import__(m)
        print(f"Success: {m}", flush=True)
    except Exception as e:
        print(f"Failed: {m} - {e}", flush=True)

print("--- FINISHED BASE MODULES ---", flush=True)

sys.path.append(".")
flowyml_modules = [
    "flowyml.core.context",
    "flowyml.core.step",
    "flowyml.core.pipeline",
    "flowyml.core.executor",
    "flowyml.core.orchestrator",
    "flowyml.assets.base",
]

for m in flowyml_modules:
    try:
        print(f"Importing {m}...", flush=True)
        __import__(m)
        print(f"Success: {m}", flush=True)
    except Exception as e:
        print(f"Failed: {m} - {e}", flush=True)
