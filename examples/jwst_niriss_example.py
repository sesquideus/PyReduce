"""
Simple usage example for PyReduce
Loads a sample JWST NIRISS dataset, and runs the full extraction
"""

import datetime
import typing

from pathlib import Path

from workflow import Workflow


class WorkflowJWST_NIRISS(Workflow):
    instrument_name: str = "JWST_NIRISS"
    night: datetime.date = None
    mode: str = "GR700XD"
    steps: list[str] = [
        "bias",
        "flat",
        "orders",
        "norm_flat",
        # "wavecal",
        # "curvature",
        "science",
        "continuum",
        "finalize"
    ]
    local_dir: Path = Path("~/astar/pyreduce/data/").expanduser()
    base_dir_template: str = None
    input_dir_template: str = "awesimsoss/"
    output_dir_template: str = "reduced/"


WorkflowJWST_NIRISS().process()
