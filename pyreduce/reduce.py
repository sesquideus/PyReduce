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

import datetime
import logging
import itertools
import os
import numpy as np
import pprint

from pathlib import Path
from typing import Any

# PyReduce subpackages
from . import __version__, instruments, util
from .configuration import load_config
from .instruments.instrument import Instrument
from .instruments.instrument_info import load_instrument
from .reducer import Reducer

from . import colour as c

# TODO Naming of functions and modules
# TODO License

# TODO automatic determination of the extraction width
logger = logging.getLogger(__name__)


def main(instrument_name: str,
         target: str | list[str] = None,
         night: datetime.date | list[datetime.date] | None = None,
         modes: str | list[str] | dict[Instrument, str] = None,
         *,
         steps: str | list[str] = "all",
         base_dir_template: str = None,
         input_dir_template: str = None,
         output_dir_template: str = None,
         configuration: dict[str, Any] = None,
         order_range: tuple[int, int] = None,
         allow_calibration_only: bool = False,
         skip_existing: bool = False):  # until converted to a class
    r"""
    Main entry point for REDUCE scripts,
    default values can be changed as required if reduce is used as a script
    Finds input directories, and loops over observation nights and instrument modes

    Parameters
    ----------
    instrument_name : str, list[str]
        instrument used for the observation (e.g. UVES, HARPS)
    target : str, list[str]
        the observed star, as named in the folder structure/fits headers
    night : str, list[str]
        the observation nights to reduce, as named in the folder structure. Accepts bash wildcards (i.e. \*, ?),
        but then relies on the folder structure for restricting the nights
    modes : str, list[str], dict[{instrument}:list], None, optional
        the instrument modes to use, if None will use all known modes for the current instrument.
        See instruments for possible options.
    steps : list(str), "all", optional
        which steps of the reduction process to perform
        the possible steps are: "bias", "flat", "orders", "norm_flat", "wavecal", "science"
        alternatively set steps to "all", which is equivalent to setting all steps
        Note that the later steps require the previous intermediary products to exist and raise an exception otherwise
    base_dir_template : str, optional
        base data directory that Reduce should work in, is prefixed on input_dir and output_dir
        (default: use settings_pyreduce.json)
    input_dir_template : str, optional
        input directory containing raw files. Can contain placeholders {instrument}, {target}, {night}, {mode}
        as well as wildcards. If relative will use base_dir as root (default: use settings_pyreduce.json)
    output_dir_template : str, optional
        output directory for intermediary and final results.
        Can contain placeholders {instrument}, {target}, {night}, {mode}, but no wildcards.
        If relative will use base_dir as root (default: use settings_pyreduce.json)
    configuration : dict[str:obj], str, list[str], dict[{instrument}:dict,str], optional
        configuration file for the current run, contains parameters for different parts of reduce.
        Can be a path to a json file, or a dict with configurations for the different instruments.
        When a list, the order must be the same as instruments (default: settings_{instrument.upper()}.json)
    debug: bool
        Show debugging info and set logger level accordingly
    """

    logger.debug(f"Running reduction for target {c.name(target)} on nights {c.name(night)}")

    # If there is a single target, create a length-1 list from it
    if isinstance(target, str) or target is None:
        targets = [target]
    else:
        targets = target

    # If there is a single night, create a length-1 list from it
    if night is None:
        nights = [None]
    elif isinstance(night, datetime.date):
        nights = [night]
    elif isinstance(night, list):
        for n in night:
            if not isinstance(n, datetime.date):
                raise TypeError(f"All nights must be instances of `datetime.date`")
        nights = night
    else:
        raise TypeError(f"Parameter 'night' must be an instance of `datetime.date` or a list thereof")

    is_none = {
        "modes": modes is None,
        "base_dir": base_dir_template is None,
        "input_dir": input_dir_template is None,
        "output_dir": output_dir_template is None,
    }
    output = []

    # Loop over everything

    # settings: default settings of PyReduce
    # config: paramters for the current reduction
    # info: constant, instrument specific parameters

    logger.trace(f"Current configuration is:\n{pprint.pformat(configuration)}")

    instrument: Instrument = instruments.instrument_info.load_instrument(instrument_name)

    config = load_config(configuration, instrument_name, 0)
    info = instrument.info

    # load default settings from settings_pyreduce.json
    if base_dir_template is None:
        base_dir_template = config["reduce"]["base_dir"]
    if input_dir_template is None:
        input_dir_template = config["reduce"]["input_dir"]
    if output_dir_template is None:
        output_dir_template = config["reduce"]["output_dir"]

    input_dir_template: str = os.path.join(base_dir_template, input_dir_template)
    logger.debug(f"input_dir_template is {c.path(input_dir_template)}")

    output_dir_template: str = os.path.join(base_dir_template, output_dir_template)
    logger.debug(f"output_dir_template is {c.path(output_dir_template)}")

    if modes is None:
        modes = info["modes"]
    if np.isscalar(modes):
        modes = [modes]

    logger.debug(f"Running over a Cartesian product of "
                 f"targets {c.print_list(targets, c.name)} × "
                 f"nights {c.print_list(nights, c.name)} × "
                 f"modes {c.print_list(modes, c.name)}")

    for target, night, mode in itertools.product(targets, nights, modes):
        assert isinstance(night, datetime.date), f"Expected night to be a `datetime.date`, got {type(night)} instead"

        log_file = (Path(base_dir_template.format(instrument=instrument.name, mode=modes, target=target)) /
                    "logs" / f"{target}.log")
        util.start_logging(log_file)
        # find input files and sort them by type
        files = instrument.classify_files(input_dir_template, target, night,
                                          mode=mode,
                                          **config["instrument"],
                                          allow_calibration_only=allow_calibration_only)
        if len(files) == 0:
            logger.warning(f"No files found for instrument {c.name(instrument.name)}, target: {c.name(target)}, "
                           f"night: {c.name(night)}, mode: {c.name(mode)} in directory {c.path(input_dir_template)}")
        else:
            for settings, filedict in files:
                logger.info("Settings:")
                for key, value in settings.items():
                    logger.info(f"\t{c.param(key)}: {c.param(value)}")

                logger.info("Input files were classified")
                for step, filelist in filedict.items():
                    logger.debug(f"\t{c.name(step)}")
                    for path in filelist:
                        logger.debug(f"\t\t{c.path(path)}")

                reducer = Reducer(
                    filedict,
                    output_dir_template,
                    settings.get("target"),
                    instrument,
                    mode,
                    settings.get("night"),
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
