"""pytest configuration and shared fixtures."""
import sys
from pathlib import Path

# Ensure the workbench root is importable
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
