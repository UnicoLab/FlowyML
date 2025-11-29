#!/usr/bin/env python3
"""Comprehensive rebranding script from flowyml/flowyml to FlowyML/flowyml"""
import re
from pathlib import Path

# Define replacements
REPLACEMENTS = [
    (r"github\.com/UnicoLab/flowyml", "github.com/UnicoLab/FlowyML"),
    (r"unicolab\.github\.io/flowyml", "unicolab.github.io/FlowyML"),
    (r"pip install flowyml", "pip install flowyml"),
    (r"pip install flowyml", "pip install flowyml"),
    (r"pypi\.org/project/flowyml", "pypi.org/project/flowyml"),
    (r"img\.shields\.io/pypi/v/flowyml", "img.shields.io/pypi/v/flowyml"),
    (r"RUN pip install flowyml", "RUN pip install flowyml"),
]

# File extensions to process
EXTENSIONS = [".md", ".yml", ".yaml", ".py", ".txt", ".toml"]

# Directories to skip
SKIP_DIRS = {
    ".git",
    "zenml-dashboard-main",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    ".flowyml",
    "site",
}


def should_process(file_path: Path) -> bool:
    """Check if file should be processed"""
    # Skip if in excluded directory
    for parent in file_path.parents:
        if parent.name in SKIP_DIRS:
            return False

    # Check extension
    return file_path.suffix in EXTENSIONS


def process_file(file_path: Path):
    """Process a single file"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Apply all replacements
        for pattern, replacement in REPLACEMENTS:
            content = re.sub(pattern, replacement, content)

        # Write back if changed
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return False


def main():
    root = Path()
    changed_files = []

    for file_path in root.rglob("*"):
        if file_path.is_file() and should_process(file_path):
            if process_file(file_path):
                changed_files.append(str(file_path))

    print(f"Updated {len(changed_files)} files")
    if changed_files:
        print("\nFiles changed:")
        for f in sorted(changed_files)[:20]:  # Show first 20
            print(f"  - {f}")
        if len(changed_files) > 20:
            print(f"  ... and {len(changed_files) - 20} more")


if __name__ == "__main__":
    main()
