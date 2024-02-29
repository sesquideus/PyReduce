"""
Simple usage example for PyReduce
Loads a ScopeSim simulated MICADO dataset (with updated spectral layout and updated line lists), and runs the full extraction. 
"""

import datetime

from pathlib import Path

from workflow import Workflow


class WorkflowMicado(Workflow):
    instrument_name: str = "MICADO"
    target: str = None
    night: datetime.date = None
    mode: str = ""
    data_url = "https://www.dropbox.com/sh/e3lnvtkmyjveajk/AABPHxeUdDO5AnkWCAjbM0e1a?dl=1"
    steps: list[str] = [
        # "bias",
        "flat",
        "orders",
        "curvature",
        # "scatter",
        # "norm_flat",
        "wavecal",
        # "science",
        # "continuum",
        # "finalize"
    ]
    local_dir: Path = Path("~/astar/pyreduce/data/").expanduser()
    base_dir_template: str = None
    input_dir_template: str = "raw_new/HK/"
    output_dir_template: str = "reduced_new/"
    order_range: tuple[int, int] = (3, 4)


if __name__ == "__main__":
    WorkflowMicado().process()

# Configuring parameters of individual steps here overwrites those defined  in the settings_MICADO.json file.
# Once you are satisfied with a certain parameter, you can update it in settings_MICADO.json.


# config["orders"]["noise"] = 100
# config["curvature"]["extraction_width"] = 350 # curvature can still be improved with this and the following parameters
# config["curvature"]["peak_threshold"] =10  
# config["curvature"]["peak_width"] =2 #CHECK 6 also works and detects one less line
# config["curvature"]["window_width"] = 5
# config["wavecal"]["extraction_width"] = 350

# NOTE: micado.thar_master.fits (created and controlled by wavecal_master) is NOT overwritten if any parameter
# in the steps in or before it are changed. Thus it has to be deleted before running PyReduce again.

# Define the path for the base, input and output directories
# The data (with fixed header keywords) can be fetched from
# https://www.dropbox.com/sh/e3lnvtkmyjveajk/AABPHxeUdDO5AnkWCAjbM0e1a?dl=0 and stored in input_dir