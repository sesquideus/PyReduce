import datetime
import logging
import os
import glob

from pathlib import Path
from typing import ClassVar
from collections import OrderedDict

from .instruments.instrument import Instrument
from .instruments.instrument_info import load_instrument
from .steps import (Step, ExtractionStep, CalibrationStep,
                    Bias, Flat, Mask, OrderTracing, SlitCurvatureDetermination, Finalize, BackgroundScatter,
                    NormalizeFlatField, RectifyImage, ScienceExtraction,
                    ContinuumNormalization, LaserFrequencyCombMaster, LaserFrequencyCombFinalize,
                    WavelengthCalibrationInitialize, WavelengthCalibrationMaster, WavelengthCalibrationFinalize)
from . import colour as c

logger = logging.getLogger(__name__)


class Reducer:
    step_order: dict[str, int] = {
        "mask": 5,  # TODO: This was not here but I do not understand why, maybe Thomas can explain
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

    modules: OrderedDict[str, ClassVar] = {
        "mask": Mask,
        "bias": Bias,
        "flat": Flat,
        "orders": OrderTracing,
        "curvature": SlitCurvatureDetermination,
        "scatter": BackgroundScatter,
        "norm_flat": NormalizeFlatField,
        "wavecal_master": WavelengthCalibrationMaster,
        "wavecal_init": WavelengthCalibrationInitialize,
        "wavecal": WavelengthCalibrationFinalize,
        "freq_comb_master": LaserFrequencyCombMaster,
        "freq_comb": LaserFrequencyCombFinalize,
        "rectify": RectifyImage,
        "science": ScienceExtraction,
        "continuum": ContinuumNormalization,
        "finalize": Finalize,
    }

    def __init__(self,
                 classified_files: dict[str, list[Path]],
                 output_dir_template: str,
                 target: str,
                 instrument: Instrument,
                 mode: str,
                 night: datetime.date,
                 config: dict,
                 *,
                 order_range=None,
                 skip_existing: bool = False):
        """Reduce all observations from a single night and instrument mode

        Parameters
        ----------
        classified_files: dict[str, Path]
            data files for each step, classified by use case
        output_dir_template : str
            directory to place output files in, should contain placeholders
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
        self.files = classified_files
        self.output_dir = output_dir_template.format(instrument=str(instrument),
                                                     target=target,
                                                     night=night,
                                                     mode=mode)

        if isinstance(instrument, str):
            instrument = load_instrument(instrument)

        self.data = {"files": classified_files, "config": config}
        self.inputs = (instrument, mode, target, night, output_dir_template, order_range)
        self.config = config
        self.skip_existing = skip_existing

    def run_module(self, step: str, load: bool = False):
        # The Module this step is based on (an object of the Step class)
        module = self.modules[step](*self.inputs, **self.config.get(step, {}))

        # Load the dependencies necessary for loading/running this step
        dependencies = module.depends_on if not load else module.load_depends_on

        for dependency in dependencies:
            if dependency not in self.data.keys():
                self.data[dependency] = self.run_module(dependency, load=True)
        kwargs = {d: self.data[d] for d in dependencies}

        # Try to load the data, if the step is not specifically given as necessary
        # If the intermediate data is not available, run it normally instead
        # But give a warning
        if load:
            try:
                logger.info(f"Loading data from step {c.step(step)}")
                data = module.load(**kwargs)
            except FileNotFoundError:
                logger.warning(f"Intermediate file(s) for loading step {c.act(step)} not found. Running it instead.")
                data = self.run_module(step, load=False)
        else:
            logger.debug(f"Running step {c.act(step)}")
            if step in self.files.keys():
                kwargs["files"] = self.files[step]

            data = module.run(**kwargs)

        self.data[step] = data
        return data

    def prepare_output_dir(self) -> None:
        """ Create output folder structure if necessary """
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def run_steps(self, steps: str | list[str] = "all"):
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
            module = self.modules["finalize"](*self.inputs,
                                              **self.config.get("finalize", {}))
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

            logger.debug(f"These steps already exists: {c.name(exists)}")

            if all(exists):
                logger.info("All science files already exist, skipping this set")
                logger.debug("--------------------------------")
                return data
        else:
            logger.info(f"Flag {c.param('skip_existing')} is {c.over('False')} or {c.param('finalize')} "
                        f"is not in steps, all steps will be performed")

        steps.sort(key=lambda x: self.step_order[x])

        for step in steps:
            self.run_module(step)

        logger.debug("--------------------------------")
        return self.data
