"""Make `personal_inflation` importable without requiring `pip install -e .`.

Imported (for its side effect) at the top of every page in this app.
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
