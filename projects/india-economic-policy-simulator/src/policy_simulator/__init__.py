"""policy_simulator — a simplified, pedagogical macroeconomic model for
exploring Indian fiscal/monetary policy trade-offs, plus an empirical
monetary-transmission module (iBFPI vs. the RBI repo rate).

Two independent surfaces, deliberately kept separate so the distinction
between MODEL (what the simulator assumes) and EMPIRICAL (what the data
actually shows) stays visible:

- ``policy_simulator.macro_model``: the AD/AS-style simulator — a teaching
  model, not a forecasting tool.
- ``policy_simulator.monetary_transmission``: the iBFPI empirical
  construction, adapted from the author's accompanying research.
"""
from .macro_model import CalibrationParams, DEFAULT_PARAMS, run_scenario, compare_scenarios

__all__ = [
    "CalibrationParams",
    "DEFAULT_PARAMS",
    "run_scenario",
    "compare_scenarios",
]

__version__ = "0.1.0"
