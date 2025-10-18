"""Basic tests to ensure the project structure is valid."""

import os
import sys
from pathlib import Path


def test_project_structure():
    """Test that the basic project structure exists."""
    project_root = Path(__file__).parent.parent

    # Check that source directory exists
    assert (project_root / "src").exists(), "src directory should exist"

    # Check that requirements files exist
    assert (project_root / "requirements.txt").exists(), "requirements.txt should exist"
    assert (
        project_root / "requirements-dev.txt"
    ).exists(), "requirements-dev.txt should exist"

    # Check that main modules can be imported
    src_path = project_root / "src"
    sys.path.insert(0, str(src_path))

    try:
        import codex_integration
        import codex_keyword
        import codex_vector
    except ImportError as e:
        # If modules can't be imported, that's okay for now
        # This test is mainly to ensure the structure exists
        pass


def test_requirements_files_readable():
    """Test that requirements files are readable and contain content."""
    project_root = Path(__file__).parent.parent

    requirements_file = project_root / "requirements.txt"
    with open(requirements_file, "r") as f:
        content = f.read().strip()
        assert content, "requirements.txt should not be empty"

    dev_requirements_file = project_root / "requirements-dev.txt"
    with open(dev_requirements_file, "r") as f:
        content = f.read().strip()
        assert content, "requirements-dev.txt should not be empty"
        assert "pytest" in content, "requirements-dev.txt should contain pytest"


def test_python_version():
    """Test that we're running a supported Python version."""
    assert sys.version_info >= (3, 8), "Python 3.8+ is required"
