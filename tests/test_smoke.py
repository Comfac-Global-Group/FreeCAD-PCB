"""Smoke tests — verify the workbench can be imported without crashing."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def test_repo_root_importable():
    """The workbench root directory must be on sys.path."""
    assert str(REPO_ROOT) in sys.path


def test_package_xml_exists():
    """package.xml must exist and declare AGPLv3."""
    pkg = REPO_ROOT / "package.xml"
    assert pkg.exists()
    text = pkg.read_text()
    assert "AGPLv3.0" in text
    assert "pythonmin>3.10.0" in text
    assert "freecadmin>0.21.0" in text


def test_no_py2_builtin_shims():
    """Python 2/3 __builtin__ shims must have been removed."""
    py_files = list(REPO_ROOT.rglob("*.py"))
    # Exclude vendored sqlalchemy and the test suite itself
    py_files = [p for p in py_files if "sqlalchemy" not in str(p) and "tests/" not in str(p)]
    offenders = []
    for p in py_files:
        text = p.read_text()
        if "import __builtin__" in text:
            offenders.append(str(p))
    assert not offenders, f"Py2 __builtin__ shims remain in: {offenders}"


def test_agpl_license_file_exists():
    """LICENSE file must contain AGPLv3 text."""
    lic = REPO_ROOT / "LICENSE"
    assert lic.exists()
    text = lic.read_text()
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in text


def test_no_vendored_sqlalchemy():
    """Vendored SQLAlchemy directory must have been removed."""
    assert not (REPO_ROOT / "sqlalchemy").exists(), "Vendored sqlalchemy/ directory should be removed; use 'pip install -r requirements.txt' instead"
