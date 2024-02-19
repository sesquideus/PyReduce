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

from os.path import dirname, join
from pathlib import Path

logger = logging.getLogger(__name__)

if int(jsonschema.__version__[0]) < 3:  # pragma: no cover
    logger.warning(
        "Jsonschema %s found, but at least 3.0.0 is required to check configuration. Skipping the check.",
        jsonschema.__version__,
    )
    hasJsonSchema = False
else:
    hasJsonSchema = True


def get_configuration_for_instrument(instrument, **kwargs):
    local = dirname(__file__)
    instrument = str(instrument)
    if instrument in ["pyreduce", None]:
        fname = join(local, "settings", f"settings_pyreduce.json")
    else:
        fname = join(local, "settings", f"settings_{instrument.upper()}.json")

    config = load_config(fname, instrument)

    for kwarg_key, kwarg_value in kwargs.items():
        for key, value in config.items():
            if isinstance(config[key], dict) and kwarg_key in config[key].keys():
                config[key][kwarg_key] = kwarg_value

    return config


def load_config(configuration, instrument: str, j: int = 0):
    logger.debug(f"Loading configuration for instrument {instrument})")

    if configuration is None:
        logger.warning("No configuration specified, using default values for this instrument")
        config = get_configuration_for_instrument(instrument, plot=False)
    elif isinstance(configuration, dict):
        if instrument in configuration.keys():
            config = configuration[str(instrument)]
        elif "__instrument__" in configuration.keys() and \
                configuration["__instrument__"] == str(instrument).upper():
            config = configuration
        else:
            raise KeyError("This configuration is for a different instrument")
    elif isinstance(configuration, list):
        config = configuration[j]
    elif isinstance(configuration, str):
        config = configuration

    if isinstance(config, str):
        logger.info("Loading configuration from %s", config)
        try:
            with open(config) as f:
                config = json.load(f)
        except FileNotFoundError:
            fname = Path(__file__).parent / "instruments" / instrument.lower() / f"settings_{instrument}.json"
            with open(fname) as f:
                config = json.load(f)

    # Combine instrument specific settings, with default values
    settings = read_config()
    settings = update(settings, config)

    # If it doesn't raise an Exception everything is as expected
    validate_config(settings)
    logger.debug("Configuration succesfully validated")

    return settings


def update(dict1, dict2, check=True, name="dict1"):
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


def read_config(fname="settings_pyreduce.json"):
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
    Otherwise show a warning but continue. This is in case some other module needs an earlier,
    jsonschema (looking at you jwst).

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
    if not hasJsonSchema:  # pragma: no cover
        # Can't check with old version
        return
    fname = Path(__file__).parent / "instruments" / "settings_schema.json"

    with open(fname) as f:
        schema = json.load(f)
    try:
        jsonschema.validate(schema=schema, instance=config)
    except jsonschema.ValidationError as ve:
        logger.error("Configuration failed validation check.\n%s", ve.message)
        raise ValueError(ve.message)
