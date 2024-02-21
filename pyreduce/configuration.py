# -*- coding: utf-8 -*-
"""Loads configuration files

This module loads json configuration files from disk,
and combines them with the default settings,
to create one dict that contains all parameters.
It also checks that all parameters exists, and that
no new parameters have been added by accident.
"""

import json
import logging
import jsonschema

from pathlib import Path

from pyreduce.util import ConfigurationError
from . import colour as c

logger = logging.getLogger(__name__)


if int(jsonschema.__version__[0]) < 3:  # pragma: no cover
    logger.warning(f"Jsonschema {jsonschema.__version__} found, but at least 3.0.0 "
                   f"is required to check configuration. Skipping the check.")
    has_json_schema = False
else:
    has_json_schema = True


def get_configuration_for_instrument(instrument_name: str, **kwargs):
    logger.trace(f"Getting configuration for instrument {c.name(instrument_name)}")
    if instrument_name in ["pyreduce", None]:
        fname = Path(__file__).parent / "settings" / "settings_pyreduce.json"
    else:
        fname = Path(__file__).parent / "instruments" / instrument_name.lower() / f"settings_{instrument_name}.json"

    config = load_config(fname, instrument_name)

    for kwarg_key, kwarg_value in kwargs.items():
        for key, value in config.items():
            if isinstance(config[key], dict) and kwarg_key in config[key].keys():
                config[key][kwarg_key] = kwarg_value

    return config


def load_config(configuration: None | str | list | dict | Path, instrument_name: str, j: int = 0):
    logger.debug(f"Loading configuration for instrument {c.name(instrument_name)}")

    # First convert to proper filename
    if configuration is None:
        logger.warning("No configuration specified, using default values for this instrument")
        config = get_configuration_for_instrument(instrument_name, plot=False)
    elif isinstance(configuration, dict):
        if instrument_name in configuration.keys():
            config = configuration[str(instrument_name)]
        elif "__instrument__" in configuration.keys() and \
                configuration["__instrument__"] == str(instrument_name).upper():
            config = configuration
        else:
            raise KeyError("This configuration is for a different instrument")
    elif isinstance(configuration, list):
        assert False, \
            "I doubt configuration from list is good, but let's see if it ever happens and if not we can remove it"
        # TODO Verify this
        config = configuration[j]
    elif isinstance(configuration, str):
        assert False, \
            "We do not expect a string here but I don't know if it is safe to remove it"
        # TODO Verify this
        config = Path(configuration)
    elif isinstance(configuration, Path):
        config = configuration
    else:
        raise TypeError(f"Configuration must be None | dict | list | str, got {type(configuration)}")

    if isinstance(config, str) or isinstance(config, Path):
        logger.info(f"Loading configuration from {config}")
        try:
            with open(config) as f:
                config = json.load(f)
        except FileNotFoundError:
            fname = Path(__file__).parent / "instruments" / instrument_name.lower() / f"settings_{instrument_name}.json"
            logger.warning(f"File {config} was not found, defaulting to {fname}")
            with open(fname) as f:
                config = json.load(f)

    # Combine instrument specific settings, with default values
    settings = read_instrument_config()
    settings = update(settings, config)

    # If it doesn't raise an Exception everything is as expected
    validate_config(settings)

    return settings


def update(dict1: dict, dict2: dict, check: bool = True, name: str = "dict1") -> dict:
    """
    Update entries in dict1 with entries of dict2 recursively,
    i.e. if the dict contains a dict value, values inside the dict will
    also be updated

    Parameters
    ----------
    dict1 : dict
        dict that will be updated
    dict2 : dict
        dict that contains the values to update
    check : bool
        If True, will check that the keys from dict2 exist in dict1 already.
        Except for those contained in field "instrument"

    Returns
    -------
    dict1 : dict
        the updated dict

    Raises
    ------
    KeyError
        If dict2 contains a key that is not in dict1
    """
    # TODO: See if this cannot be converted to new | syntax for dicts
    # Instrument is a 'special' section as it may include any number of values
    # In that case we don't want to raise an error for new keys
    exclude = ["instrument"]

    for key, value in dict2.items():
        if check and key not in dict1.keys():
            logger.warning(f"{key} is not contained in {name}")
        if isinstance(value, dict):
            dict1[key] = update(dict1[key], value, check=key not in exclude, name=key)
        else:
            dict1[key] = value
    return dict1


def read_instrument_config(fname="settings_pyreduce.json"):
    """Read the configuration file from disk

    If no filename is given it will load the default configuration.
    The configuration file must be a json file.

    Parameters
    ----------
    fname : str, optional
        Filename of the configuration. Default "settings_pyreduce.json",
        i.e. the default configuration

    Returns
    -------
    config : dict
        The read configuration file
    """
    fname = Path(__file__).parent / "instruments" / fname
    with open(fname) as file:
        settings = json.load(file)
        return settings


def validate_config(config) -> None:
    """Test that the input configuration complies with the expected schema

    Since it requires features from jsonschema 3+, it will only run if that is installed.
    Otherwise, show a warning but continue. This is in case some other module needs an earlier
    jsonschema (looking at you JWST).

    If the function runs through without raising an exception, the check was successful or skipped.

    Parameters
    ----------
    config : dict
        Configurations to check

    Raises
    ------
    ValueError
        If there is a problem with the configuration.
        Usually that means a setting has an unallowed value.
    """
    if has_json_schema:  # pragma: no cover
        fname = Path(__file__).parent / "instruments" / "settings_schema.json"

        with open(fname) as f:
            schema = json.load(f)
        try:
            jsonschema.validate(schema=schema, instance=config)
            logger.debug(f"Configuration was successfully validated against schema {c.path(fname)}.")
        except jsonschema.ValidationError as exc:
            logger.critical(f"Configuration failed validation check: {exc.message}")
            raise ConfigurationError("Could not validate instrument configuration") from exc
    else:
        logger.warning("Module `jsonschema` is not imported, configuration validation skipped")
