"""
Simple usage example for PyReduce
Loads a sample JWST MIRI dataset, and runs the full extraction
"""

import datetime

from pathlib import Path

from workflow import Workflow


class WorkflowJWST_MIRI(Workflow):
    instrument_name: str = "JWST_MIRI"
    night: datetime.date = None
    mode: str = "LRS_SLITLESS"
    steps: list[str] = [
        "bias",
        "flat",
        "orders",
        "norm_flat",
        # "wavecal",
        # "curvature",
        "science",
        # "continuum",
        # "finalize",
    ]
    local_dir: Path = Path("~/astar/pyreduce/data/").expanduser()
    base_dir_template: str = None
    input_dir_template: str = "raw/"
    output_dir_template: str = "reduced/"


WorkflowJWST_MIRI().process()
