# -*- coding: utf-8 -*-
"""
Simple usage example for PyReduce
Loads a sample UVES dataset, and runs the full extraction
"""

import os.path

from pyreduce import datasets
from workflow import Workflow


class WorkflowXShooter(Workflow):
    instrument = "XShooter"
    target = "UX-Ori"
    night = None
    mode = "NIR"
    steps = ["bias", "flat", "orders", "scatter", "norm_flat",
             "curvature", "wavecal", "science", "continuum", "finalize"]
    base_dir_template = datasets.UVES(os.path.expanduser("~") + "/PyReduce/DATA")
    input_dir_template = "raw/"
    output_dir_template = "reduced/"
    order_range = (0, 15)
    debug = True

    def override_configuration(self, **kwargs):
        # self.configuration["science"]["extraction_method"] = "arc"
        # self.configuration["science"]["extraction_cutoff"] = 0
        pass

# some basic settings
# Expected Folder Structure: base_dir/datasets/HD132205/*.fits.gz
# Feel free to change this to your own preference, values in curly brackets will be replaced with the actual values {}


WorkflowXShooter().process()
