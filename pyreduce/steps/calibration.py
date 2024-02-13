import abc

from .step import Step

from pyreduce.combine_frames import combine_calibrate


class CalibrationStep(Step, metaclass=abc.ABCMeta):
    def __init__(self, *args, **config):
        super().__init__(*args, **config)
        self._dependsOn += ["mask", "bias"]

        # {'number_of_files', 'exposure_time', 'mean', 'median', 'none'}:
        # how to adjust for diferences between the bias and flat field exposure times
        self.bias_scaling = config["bias_scaling"]
        # {'divide', 'none'}: how to apply the normalized flat field
        self.norm_scaling = config["norm_scaling"]

    def calibrate(self, files, mask, bias=None, norm_flat=None):
        bias, bhead = bias if bias is not None else (None, None)
        norm, blaze = norm_flat if norm_flat is not None else (None, None)
        orig, thead = combine_calibrate(
            files,
            self.instrument,
            self.mode,
            mask,
            bias=bias,
            bhead=bhead,
            norm=norm,
            bias_scaling=self.bias_scaling,
            norm_scaling=self.norm_scaling,
            plot=self.plot,
            plot_title=self.plot_title,
        )

        return orig, thead