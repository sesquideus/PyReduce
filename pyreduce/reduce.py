# -*- coding: utf-8 -*-
"""
REDUCE script for spectrograph data

Authors
-------
Ansgar Wehrhahn  (ansgar.wehrhahn@physics.uu.se)
Thomas Marquart  (thomas.marquart@physics.uu.se)
Alexis Lavail    (alexis.lavail@physics.uu.se)
Nikolai Piskunov (nikolai.piskunov@physics.uu.se)

Version
-------
1.0 - Initial PyReduce

License
--------
...

"""
import glob
import logging
import os.path
from itertools import product
from pathlib import Path

import numpy as np

# PyReduce subpackages
from . import __version__, instruments, util
from .configuration import load_config
from .instruments.instrument_info import load_instrument

from pyreduce.steps import (Bias, Flat, Mask, OrderTracing, SlitCurvatureDetermination, Finalize, BackgroundScatter,
                            NormalizeFlatField, RectifyImage, ScienceExtraction,
                            ContinuumNormalization, LaserFrequencyCombMaster, LaserFrequencyCombFinalize,
                            WavelengthCalibrationInitialize, WavelengthCalibrationMaster, WavelengthCalibrationFinalize)

# TODO Naming of functions and modules
# TODO License

# TODO automatic determination of the extraction width
logger = logging.getLogger(__name__)


def main(instrument,
         target,
         night: str | None = None,
         modes=None,
         steps: str | tuple = "all",
         *,
         base_dir=None,
         input_dir=None,
         output_dir=None,
         configuration=None,
         order_range=None,
         allow_calibration_only=False,
         skip_existing=False):
    r"""
    Main entry point for REDUCE scripts,
    default values can be changed as required if reduce is used as a script
    Finds input directories, and loops over observation nights and instrument modes

    Parameters
    ----------
    instrument : str, list[str]
        instrument used for the observation (e.g. UVES, HARPS)
    target : str, list[str]
        the observed star, as named in the folder structure/fits headers
    night : str, list[str]
        the observation nights to reduce, as named in the folder structure. Accepts bash wildcards (i.e. \*, ?),
        but then relies on the folder structure for restricting the nights
    modes : str, list[str], dict[{instrument}:list], None, optional
        the instrument modes to use, if None will use all known modes for the current instrument.
        See instruments for possible options.
    steps : tuple(str), "all", optional
        which steps of the reduction process to perform
        the possible steps are: "bias", "flat", "orders", "norm_flat", "wavecal", "science"
        alternatively set steps to "all", which is equivalent to setting all steps
        Note that the later steps require the previous intermediary products to exist and raise an exception otherwise
    base_dir : str, optional
        base data directory that Reduce should work in, is prefixed on input_dir and output_dir
        (default: use settings_pyreduce.json)
    input_dir : str, optional
        input directory containing raw files. Can contain placeholders {instrument}, {target}, {night}, {mode}
        as well as wildcards. If relative will use base_dir as root (default: use settings_pyreduce.json)
    output_dir : str, optional
        output directory for intermediary and final results.
        Can contain placeholders {instrument}, {target}, {night}, {mode}, but no wildcards.
        If relative will use base_dir as root (default: use settings_pyreduce.json)
    configuration : dict[str:obj], str, list[str], dict[{instrument}:dict,str], optional
        configuration file for the current run, contains parameters for different parts of reduce.
        Can be a path to a json file, or a dict with configurations for the different instruments.
        When a list, the order must be the same as instruments (default: settings_{instrument.upper()}.json)
    """
    if target is None or np.isscalar(target):
        target = [target]
    if night is None or np.isscalar(night):
        night = [night]

    isNone = {
        "modes": modes is None,
        "base_dir": base_dir is None,
        "input_dir": input_dir is None,
        "output_dir": output_dir is None,
    }
    output = []

    # Loop over everything

    # settings: default settings of PyReduce
    # config: paramters for the current reduction
    # info: constant, instrument specific parameters
    config = load_config(configuration, instrument, 0)
    if isinstance(instrument, str):
        instrument = instruments.instrument_info.load_instrument(instrument)
    info = instrument.info

    # load default settings from settings_pyreduce.json
    if base_dir is None:
        base_dir = config["reduce"]["base_dir"]
    if input_dir is None:
        input_dir = config["reduce"]["input_dir"]
    if output_dir is None:
        output_dir = config["reduce"]["output_dir"]

    input_dir = os.path.join(base_dir, input_dir)
    output_dir = os.path.join(base_dir, output_dir)

    if modes is None:
        modes = info["modes"]
    if np.isscalar(modes):
        modes = [modes]

    for t, n, m in product(target, night, modes):
        log_file = os.path.join(
            base_dir.format(instrument=str(instrument), mode=modes, target=t),
            "logs/%s.log" % t,
        )
        util.start_logging(log_file)
        # find input files and sort them by type
        files = instrument.sort_files(
            input_dir,
            t,
            n,
            mode=m,
            **config["instrument"],
            allow_calibration_only=allow_calibration_only,
        )
        if len(files) == 0:
            logger.warning(
                f"No files found for instrument: %s, target: %s, night: %s, mode: %s in folder: %s",
                instrument,
                t,
                n,
                m,
                input_dir,
            )
            continue
        for k, f in files:
            logger.info("Settings:")
            for key, value in k.items():
                logger.info("%s: %s", key, value)
            logger.debug("Files:\n%s", f)

            reducer = Reducer(
                f,
                output_dir,
                k.get("target"),
                instrument,
                m,
                k.get("night"),
                config,
                order_range=order_range,
                skip_existing=skip_existing,
            )
            # try:
            data = reducer.run_steps(steps=steps)
            output.append(data)
            # except Exception as e:
            #     logger.error("Reduction failed with error message: %s", str(e))
            #     logger.info("------------")
    return output


class Reducer:
    step_order = {
        "bias": 10,
        "flat": 20,
        "orders": 30,
        "curvature": 40,
        "scatter": 45,
        "norm_flat": 50,
        "wavecal_master": 60,
        "wavecal_init": 64,
        "wavecal": 67,
        "freq_comb_master": 70,
        "freq_comb": 72,
        "rectify": 75,
        "science": 80,
        "continuum": 90,
        "finalize": 100,
    }

    modules = {
        "mask": Mask,
        "bias": Bias,
        "flat": Flat,
        "orders": OrderTracing,
        "scatter": BackgroundScatter,
        "norm_flat": NormalizeFlatField,
        "wavecal_master": WavelengthCalibrationMaster,
        "wavecal_init": WavelengthCalibrationInitialize,
        "wavecal": WavelengthCalibrationFinalize,
        "freq_comb_master": LaserFrequencyCombMaster,
        "freq_comb": LaserFrequencyCombFinalize,
        "curvature": SlitCurvatureDetermination,
        "science": ScienceExtraction,
        "continuum": ContinuumNormalization,
        "finalize": Finalize,
        "rectify": RectifyImage,
    }

    def __init__(
            self,
            files,
            output_dir,
            target,
            instrument,
            mode,
            night,
            config,
            order_range=None,
            skip_existing=False,
    ):
        """Reduce all observations from a single night and instrument mode

        Parameters
        ----------
        files: dict{str:str}
            Data files for each step
        output_dir : str
            directory to place output files in
        target : str
            observed targets as used in directory names/fits headers
        instrument : str
            instrument used for observations
        mode : str
            instrument mode used (e.g. "red" or "blue" for HARPS)
        night : str
            Observation night, in the same format as used in the directory structure/file sorting
        config : dict
            numeric reduction specific settings, like pixel threshold, which may change between runs
        info : dict
            fixed instrument specific values, usually header keywords for gain, readnoise, etc.
        skip_existing : bool
            Whether to skip reductions with existing output
        """
        #:dict(str:str): Filenames sorted by usecase
        self.files = files
        self.output_dir = output_dir.format(
            instrument=str(instrument), target=target, night=night, mode=mode
        )

        if isinstance(instrument, str):
            instrument = load_instrument(instrument)

        self.data = {"files": files, "config": config}
        self.inputs = (instrument, mode, target, night, output_dir, order_range)
        self.config = config
        self.skip_existing = skip_existing

    def run_module(self, step, load=False):
        # The Module this step is based on (An object of the Step class)
        module = self.modules[step](*self.inputs, **self.config.get(step, {}))

        # Load the dependencies necessary for loading/running this step
        dependencies = module.dependsOn if not load else module.loadDependsOn
        for dependency in dependencies:
            if dependency not in self.data.keys():
                self.data[dependency] = self.run_module(dependency, load=True)
        args = {d: self.data[d] for d in dependencies}

        # Try to load the data, if the step is not specifically given as necessary
        # If the intermediate data is not available, run it normally instead
        # But give a warning
        if load:
            try:
                logger.info("Loading data from step '%s'", step)
                data = module.load(**args)
            except FileNotFoundError:
                logger.warning(
                    "Intermediate File(s) for loading step %s not found. Running it instead.",
                    step,
                )
                data = self.run_module(step, load=False)
        else:
            logger.info("Running step '%s'", step)
            if step in self.files.keys():
                args["files"] = self.files[step]
            data = module.run(**args)

        self.data[step] = data
        return data

    def prepare_output_dir(self):
        """ Create output folder structure if necessary """
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def run_steps(self, steps: str = "all"):
        """
        Execute the steps as required

        Parameters
        ----------
        steps : {tuple(str), "all"}, optional
            which steps of the reduction process to perform
            the possible steps are: "bias", "flat", "orders", "norm_flat", "wavecal", "freq_comb",
            "curvature", "science", "continuum", "finalize"
            alternatively set steps to "all", which is equivalent to setting all steps
        """
        self.prepare_output_dir()

        if steps == "all":
            steps = list(self.step_order.keys())
        steps = list(steps)

        if self.skip_existing and "finalize" in steps:
            module = self.modules["finalize"](
                *self.inputs, **self.config.get("finalize", {})
            )
            exists = [False] * len(self.files["science"])
            data = {"finalize": [None] * len(self.files["science"])}
            for i, f in enumerate(self.files["science"]):
                fname_in = os.path.basename(f)
                fname_in = os.path.splitext(fname_in)[0]
                fname_out = module.output_file("?", fname_in)
                fname_out = glob.glob(fname_out)
                exists[i] = len(fname_out) != 0
                if exists[i]:
                    data["finalize"][i] = fname_out[0]
            if all(exists):
                logger.info("All science files already exist, skipping this set")
                logger.debug("--------------------------------")
                return data

        steps.sort(key=lambda x: self.step_order[x])

        for step in steps:
            self.run_module(step)

        logger.debug("--------------------------------")
        return self.data
