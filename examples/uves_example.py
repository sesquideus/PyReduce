#!/usr/env/bin python
"""
Simple usage example for PyReduce
Loads a sample UVES dataset, and runs the full extraction
"""

import datetime

from workflow import Workflow


class WorkflowExampleUVES(Workflow):
    instrument_name: str = "UVES"
    target: str = r"HD[ -]?132205"
    night: datetime.date = datetime.date(2010, 4, 1)
    mode: str = "middle"
    steps: list[str] = [
        "bias",
        "flat",
        "orders",
        "norm_flat",
        "wavecal",
        "curvature",
        "science",
        "continuum",
        "finalize"
    ]
    base_dir_template: str = None
    input_dir_template: str = "raw/"
    output_dir_template: str = "reduced/{night}/{mode}"
    order_range: tuple[int, int] = (1, 21)

# some basic settings
# Expected Folder Structure: base_dir/datasets/HD132205/*.fits.gz
# Feel free to change this to your own preference, values in curly brackets will be replaced with the actual values {}


if __name__ == "__main__":
    WorkflowExampleUVES().process()
