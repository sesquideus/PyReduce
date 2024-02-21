"""
Simple usage example for PyReduce
Loads a sample UVES dataset, and runs the full extraction
"""
import datetime
import typing
from pathlib import Path

from pyreduce.datasets import DatasetXSHOOTER
from workflow import Workflow


class WorkflowXShooter(Workflow):
    instrument_name: str = "XSHOOTER"
    target: str = "UX-Ori"
    night: datetime.date = None
    mode: str = "NIR"
    steps: list[str] = ["bias", "flat", "orders", "scatter", "norm_flat",
                        "curvature", "wavecal", "science", "continuum", "finalize"]
    input_dir_template: str = "raw/"
    output_dir_template: str = "reduced/"
    order_range: tuple[int, int] = (0, 15)

    def override_configuration(self, **kwargs):
        # self.configuration["science"]["extraction_method"] = "arc"
        # self.configuration["science"]["extraction_cutoff"] = 0
        pass


# some basic settings
# Expected Folder Structure: base_dir/datasets/Ux-Ori/*.fits.gz
# Feel free to change this to your own preference, values in curly brackets will be replaced with the actual values {}


WorkflowXShooter().process()
