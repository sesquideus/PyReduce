"""
Simple usage example for PyReduce
Loads a sample HARPS dataset, and runs the full extraction
"""

import datetime

from pathlib import Path
from typing import ClassVar

from pyreduce.datasets import DatasetHARPS
from workflow import Workflow


# some basic settings
# Expected Folder Structure: base_dir/datasets/HD132205/*.fits.gz
# Feel free to change this to your own preference, values in curly brackets will be replaced with the actual values {}

# instrument = HARPS()
# files = instrument.find_files(base_dir + "/" + input_dir)
# ev = instrument.get_expected_values(None, None, "red", None, True)
# files = instrument.apply_filters(files, ev)


class WorkflowExampleHARPS(Workflow):
    instrument_name: str = "HARPS"
    dataset_class: ClassVar = DatasetHARPS
    target: str = "HD109200"
    night: datetime.date = None
    mode: str = "red"
    steps: list[str] = [
        "bias",
        "flat",
        "orders",
        "curvature",
        "scatter",
        "norm_flat",
        "wavecal",
        "freq_comb",
        "science",
        "continuum",
        "finalize",
    ]
    local_dir: Path = Path("~/astar/pyreduce/data/").expanduser()
    base_dir_template: str = None
    input_dir_template: str = "raw"
    output_dir_template: str = "reduced_{mode}"
    order_range: tuple[int, int] = (0, 25)


WorkflowExampleHARPS().process()