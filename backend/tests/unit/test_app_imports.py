import subprocess
import sys
from pathlib import Path

import pytest

ENTRY_POINTS = ["app.main", "app.cli", "app.search.projector", "app.seed", "app.workflows.worker"]


@pytest.mark.parametrize("module", ENTRY_POINTS)
def test_entry_points_configure_all_mappers_on_their_own(module):
    """Each process entry point (api, cli, projector, seed) must be able to use the ORM without the test suite's imports."""
    code = f"import {module}; from sqlalchemy.orm import configure_mappers; configure_mappers(); print('ok')"
    res = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr[-800:]
