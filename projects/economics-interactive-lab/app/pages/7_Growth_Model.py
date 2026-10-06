import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import render_module_page
from econ_lab.registry import get_module

render_module_page(get_module("macro_growth"))
