"""
Simple usage example for PyReduce
Loads a simulated METIS dataset, and runs the full extraction
By Nadeen Sabha
"""

import datetime

from pathlib import Path

from workflow import Workflow


# some basic settings
# Expected Folder Structure: base_dir/datasets/METIS/*.fits.gz or *.fits

# The data can be fetched from https://www.dropbox.com/sh/h1dz80vsw4lwoel/AAAqJD_FGDGC-t12wgnPXVR8a?dl=0
# and stored in /raw/

# Nadeen's laptop
# base_dir = "/Users/Nadeen/Dropbox/WORKING/iMETIS/Working/WORKING_PyReduce/DATA/datasets/METIS/"
# an example path which you should change to your preferred one
# Nadeen's PC
# base_dir ="/media/data/Dropbox/Dropbox/WORKING/iMETIS/Working/WORKING_PyReduce/DATA/datasets/METIS/"

# Configuring parameters of individual steps here overwrites those defined in the settings_METIS.json file.
# Once you are satisfied with the chosen parameter, you can update it in settings_METIS.json.

# config["orders"]["noise"] = 120 

# config["curvature"]['dimensionality']= '1D'
# config["curvature"]['curv_degree']= 2 
# config["curvature"]["extraction_width"] = 0.7700
# config["curvature"]["peak_threshold"] = 0.9725
# config["curvature"]["peak_width"] = 1# 1 worked for lband
# config["curvature"]["window_width"] = 1 #  2 worked for lband
# config["curvature"]["degree"] = 2 #
# config["wavecal"]["extraction_width"] = 0.7825 # 0.7325


class WorkflowExampleMETIS(Workflow):
    instrument_name: str = "METIS"
    data_url: str = "https://www.dropbox.com/sh/h1dz80vsw4lwoel/AAAqJD_FGDGC-t12wgnPXVR8a"
    target: str = r"HD[- ]?132205"
    night: datetime.date = datetime.date(2010, 4, 1)
    mode: str = "LSS_M"  # LSS_M (settings_metis.json is now optimized for LSS_M mode)
    steps: list[str] = [
        # "bias",
        "flat",
        "orders",
        "curvature",
        # "scatter",
        # "norm_flat",
        "wavecal_master",
        # # "wavecal_init",
        "wavecal",
        # "rectify",
        # "science",
        # "continuum",
        # "finalize",
    ]
    local_dir: Path = Path("~/astar/pyreduce/data/").expanduser()
    base_dir_template: str = None
    input_dir_template: str = "raw/"
    output_dir_template: str = "reduced/"
    # I had to change it inside reduce.py because it does the fix_column_range
    # for all detected orders > outside of image
    order_range: tuple[int, int] = (16, 17)

# some basic settings
# feel free to change this to your own preference, values in curly brackets will be replaced with the actual values {}


WorkflowExampleMETIS().process()
