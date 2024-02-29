"""
Simple usage example for PyReduce
Loads a sample NIRSPEC dataset, and runs the full extraction
"""

import datetime

from workflow import Workflow


class WorkflowExampleNIRSPEC(Workflow):
    instrument_name: str = "NIRSPEC"
    target: str = r"GJ1214"
    night: datetime.date = None
    mode: str = "NIRSPEC"
    steps: list[str] = [
        "bias",
        "flat",
        "orders",
        "norm_flat",
        "wavecal",
        "freq_comb",
        # "curvature",
        "science",
        # "continuum",
        "finalize"
    ]
    base_dir_template: str = None
    input_dir_template: str = "raw"
    output_dir_template: str = "reduced"
    # order_range: tuple[int, int] = (0, 25)

# some basic settings
# Expected Folder Structure: base_dir/datasets/HD132205/*.fits.gz
# Feel free to change this to your own preference, values in curly brackets will be replaced with the actual values {}


if __name__ == "__main__":
    WorkflowExampleNIRSPEC().process()
