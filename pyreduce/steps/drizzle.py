import abc
import numpy as np

from pathlib import Path

from pyreduce.combine_frames import combine_calibrate
from .step import Step


class DrizzleStep(Step, metaclass=abc.ABCMeta):
    def __init__(self, *args, **config):
        super().__init__(*args, **config)
        self._depends_on += ["mask", "bias"]

        # {'number_of_files', 'exposure_time', 'mean', 'median', 'none'}:
        # how to adjust for diferences between the bias and flat field exposure times
        self.bias_scaling = config["bias_scaling"]
        # {'divide', 'none'}: how to apply the normalized flat field
        self.norm_scaling = config["norm_scaling"]

