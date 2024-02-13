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
import logging
import itertools
import os

import numpy as np

# PyReduce subpackages
from . import __version__, instruments, util
from .configuration import load_config
from .instruments.common import Instrument
from .instruments.instrument_info import load_instrument
from .reducer import Reducer

# TODO Naming of functions and modules
# TODO License

# TODO automatic determination of the extraction width
logger = logging.getLogger(__name__)


def main(instrument_name: str,
         target,
         night: str | None = None,
         modes=None,
         steps: str | list[str] = "all",
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

    is_none = {
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

    instrument: Instrument = instruments.instrument_info.load_instrument(instrument_name)

    config = load_config(configuration, instrument_name, 0)
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

    for t, n, m in itertools.product(target, night, modes):
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
