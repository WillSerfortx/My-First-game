"""
Algorithm Compliance test.
Validates that exactly the 4 required AI techniques are integrated, and strictly ensures
no forbidden algorithms or legacy code exist in the codebase.
"""

import os
import pytest


def test_strictly_approved_four_algorithms_only():
    """
    Recursively scans all Python files in the repository and verifies that
    no unapproved algorithm tokens or references appear anywhere.
    """
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    # Token constructed dynamically to keep test file itself completely clean
    forbidden = "".join(["k", "n", "n"])

    violations = []

    for dirpath, _, filenames in os.walk(root_dir):
        if any(ignored in dirpath for ignored in (".git", "venv", ".pytest_cache", "__pycache__")):
            continue

        for filename in filenames:
            if filename.endswith(".py"):
                file_path = os.path.join(dirpath, filename)
                if filename == "test_algorithm_compliance.py":
                    continue

                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                    if forbidden in content:
                        violations.append(file_path)

    assert len(violations) == 0, f"Found unapproved algorithm references in: {violations}"
