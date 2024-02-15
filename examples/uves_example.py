"""
Simple usage example for PyReduce
Loads a sample UVES dataset, and runs the full extraction
"""
import datetime

from pathlib import Path

from pyreduce.datasets import DatasetUVES
from workflow import Workflow


class WorkflowExampleUVES(Workflow):
    instrument = "UVES"
    target = r"HD[- ]?132205"
    night = datetime.date(2010, 4, 1)
    mode = "middle"
    steps = ["bias", "flat", "orders", "norm_flat", "wavecal", "curvature", "science", "continuum", "finalize"]
    base_dir_template = str(DatasetUVES(local_dir_template=str(Path("~/astar/pyreduce/data/").expanduser())).data_dir)
    input_dir_template = "raw/"
    output_dir_template = "reduced/{night}/{mode}"
    order_range = (1, 21)
    debug = True

# some basic settings
# Expected Folder Structure: base_dir/datasets/HD132205/*.fits.gz
# Feel free to change this to your own preference, values in curly brackets will be replaced with the actual values {}


WorkflowExampleUVES().process()
