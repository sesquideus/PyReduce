"""
Simple usage example for PyReduce
Loads a sample UVES dataset, and runs the full extraction
"""

import datetime
import os.path

import pyreduce
from pyreduce import datasets
from pyreduce.configuration import get_configuration_for_instrument

# define parameters
instrument = "Crires_plus"
target = None
night = datetime.date(2021, 8, 24)
mode = "J1228_Open_det1"
steps = [
    # "bias",
    # "flat",
    # "orders",
    # "curvature",
    # "scatter",
    # "norm_flat",
    # "wavecal_master",
    # "wavecal_init",
    # "wavecal",
    "freq_comb_master",
    "freq_comb",
    # "science",
    # "continuum",
    # "finalize",
]

# some basic settings
# Expected Folder Structure: base_dir/datasets/HD132205/*.fits.gz
# Feel free to change this to your own preference, values in curly brackets will be replaced with the actual values {}

# load dataset (and save the location)
base_dir_template = "./DATA/ESO/CRIRES+/pCOMM/210824_mincal"
input_dir_template = "J1228/"
output_dir_template = "{mode}_reduced/"

# Path to the configuration parameters, that are to be used for this reduction

config = get_configuration_for_instrument(
    instrument, plot=1, bias_scaling="exposure_time"
)

pyreduce.reduce.main(
    instrument,
    target,
    night,
    mode,
    steps=steps,
    base_dir_template=base_dir_template,
    input_dir_template=input_dir_template,
    output_dir_template=output_dir_template,
    configuration=config,
    allow_calibration_only=True,
    # order_range=(0, 4),
)
