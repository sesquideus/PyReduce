"""
Simple usage example for PyReduce
Loads a sample UVES dataset, and runs the full extraction
"""
import datetime
import os.path

import pyreduce
from pyreduce import datasets
from workflow import Workflow


class WorkflowUVES(Workflow):
    instrument = "UVES"
    target = r"HD[- ]?132205"
    night = datetime.date(2010, 4, 1)
    mode = "middle"
    steps = ["bias", "flat", "orders", "norm_flat", "wavecal", "curvature", "science", "continuum", "finalize"]
    base_dir = datasets.UVES(os.path.expanduser("~") + "/PyReduce/DATA")
    input_dir = "raw/"
    output_dir = "reduced/{night}/{mode}"
    order_range = (1, 21)


# some basic settings
# Expected Folder Structure: base_dir/datasets/HD132205/*.fits.gz
# Feel free to change this to your own preference, values in curly brackets will be replaced with the actual values {}

WorkflowUVES().process()
