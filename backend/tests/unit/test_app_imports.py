import subprocess
import sys
from pathlib import Path


def test_app_registers_all_orm_mappers_on_its_own():
    """The API process (not just the test suite) must import every model so relationships resolve."""
    code = "import app.main; from sqlalchemy.orm import configure_mappers; configure_mappers(); print('ok')"
    res = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr[-800:]
