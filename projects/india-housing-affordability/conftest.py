"""Make `src/` importable without requiring an editable install, so `pytest`
works immediately after clone + `pip install -r requirements.txt`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
