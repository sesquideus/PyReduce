"""
Abstract parent module for all other instruments
Contains some general functionality, which may be overridden by the children of course
"""
import abc
import datetime
import glob
import itertools
import json
import logging
import os.path
import pprint
import typing

import numpy as np

from astropy.io import fits
from astropy.time import Time
from dateutil import parser
from pathlib import Path
from tqdm import tqdm
from typing import Any, Iterable

from ..clipnflip import clipnflip
from .filters import Filter, InstrumentFilter, ModeFilter, NightFilter, ObjectFilter
from ..util import ConfigurationError
from .. import colour as c

logger = logging.getLogger(__name__)


def find_first_index(arr, value):
    """find the first element equal to value in the array arr"""
    try:
        return next(i for i, v in enumerate(arr) if v == value)
    except StopIteration:
        raise KeyError("Value %s not found" % value)


def observation_date_to_night(observation_date: datetime.date) -> datetime.date | None:
    """Convert an observation timestamp into the date of the observation night
    Nights start at 12am and end at 12 am the next day
    TODO: How is this supposed to handle UTC?

    Parameters
    ----------
    observation_date : datetime
        timestamp of the observation

    Returns
    -------
    night : datetime.date | None
        night of the observation
        or None if the date cannot be parsed
    """
    if observation_date == "":
        return None

    observation_date = parser.parse(observation_date)

    if observation_date.hour < 12:
        observation_date -= datetime.timedelta(days=1)

    return observation_date.date()


class HeaderGetter:
    """Get data from a header/dict, based on the given mode, and applies replacements"""

    def __init__(self, header: fits.Header, info, mode):
        self.header = header
        self.info = info.copy()
        try:
            self.index = find_first_index(info["modes"], mode.upper())
        except KeyError:
            logger.warning("No instrument modes found in instrument info")
            self.index = 0

        # Pick values for the given mode
        for k, v in self.info.items():
            if isinstance(v, list):
                self.info[k] = v[self.index]

    def __call__(self, key: str, default: Any = None):
        return self.get(key, default)

    def get(self, key: str, default: Any = None):
        """Get data

        Parameters
        ----------
        key : str
            key of the data in the header
        default : obj, optional
            alternative value, if key does not exist (default: None)

        Returns
        -------
        value : obj
            value found in header (or alternatively alt)
        """

        value = self.info.get(key, key)
        # if isinstance(value, list):
        #     value = value[self.index]
        if isinstance(value, str):
            value = value.format(**self.info)
            value = self.header.get(value, default)
        return value


class Instrument(metaclass=abc.ABCMeta):
    """
    Abstract parent class for all instruments
    Handles the instrument specific information
    """

    def __init__(self):
        # Name of the instrument (lowercase)
        self.name: str = self.__class__.__name__.lower()
        # Information about the instrument
        self.info: dict[str, Any] = self.load_info()

        self.filters = {
            "instrument": InstrumentFilter(self.info["instrument"], regex=True),
            "night": NightFilter(
                self.info["date"], timeformat=self.info.get("date_format", "fits")
            ),
            "target": ObjectFilter(self.info["target"], regex=True),
            "bias": Filter(self.info["kw_bias"]),
            "flat": Filter(self.info["kw_flat"]),
            "orders": Filter(self.info["kw_orders"]),
            "curvature": Filter(self.info["kw_curvature"]),
            "scatter": Filter(self.info["kw_scatter"]),
            "wave": Filter(self.info["kw_wave"]),
            "comb": Filter(self.info["kw_comb"]),
            "spec": Filter(self.info["kw_spec"]),
        }

        self.night: str = "night"
        self.science: str = "science"
        self.shared: list[str] = ["instrument", "night"]
        # TODO What does this mean?
        self.find_closest = [
            "bias",
            "flat",
            "wavecal_master",
            "freq_comb_master",
            "orders",
            "scatter",
            "curvature",
        ]

    def __str__(self):
        return self.name

    def get(self,
            key: str,
            header: fits.Header,
            mode: str,
            default: Any = None):
        get = HeaderGetter(header, self.info, mode)
        return get(key, default=default)

    def get_extension(self, header, mode):
        mode = mode.upper()
        extension = self.info.get("extension", 0)

        if isinstance(extension, list):
            imode = find_first_index(self.info["modes"], mode)
            extension = extension[imode]

        return extension

    def load_info(self) -> dict[str, Any]:
        """
        Load static instrument information
        Either as fits header keywords or static values

        Returns
        ------
        info : dict(str:object)
            dictionary of REDUCE names for properties to Header keywords/static values
        """
        # Tips & Tricks:
        # if several modes are supported, use a list for modes
        # if a value changes depending on the mode, use a list with the same order as "modes"
        # you can also use values from this dictionary as placeholders using {name}, just like str.format

        fname = Path(__file__).parent / self.name / f"{self.name}.json"

        with open(fname) as f:
            try:
                info = json.load(f)
            except FileNotFoundError as exc:
                logger.critical(f"Could not load info for instrument {self.name}: file not found")
                raise ConfigurationError("Instrument configuration failed") from exc
            except (TypeError, json.JSONDecodeError) as exc:
                logger.critical(f"Could not load info for instrument {self.name} from file {fname}")
                raise ConfigurationError("Instrument configuration failed") from exc
        return info

    def load_fits(self,
                  fname: Path,
                  mode: str,
                  *,
                  extension: int = None,
                  mask: np.ndarray[float] = None,
                  header_only: bool = False,
                  dtype: np.dtype = np.float64
                  ) -> fits.Header | tuple[np.ma.masked_array, fits.Header]:  # TODO Maybe a sensible default here?
        """
        load fits file, REDUCE style

        primary and extension header are combined
        modeinfo is applied to header
        data is clipnflipped
        mask is applied

        Parameters
        ----------
        *
        fname : str
            filename
        mode : str
            instrument mode
        extension : int
            data extension of the FITS file to load
        mask : array, optional
            mask to add to the data
        header_only : bool, optional
            only load the header, not the data
        dtype : str, optional
            numpy datatype to convert the read data to

        Returns
        --------
        data : masked_array
            FITS data, clipped and flipped, and with mask
        header : fits.Header
            FITS header (Primary and Extension + Modeinfo)

        ONLY the header is returned if header_only is True
        """
        logger.debug(f"Loading a FITS file {c.path(fname)}")

        hdu = fits.open(fname)
        h_prime = hdu[0].header
        if extension is None:
            extension = self.get_extension(h_prime, mode.upper())

        header = hdu[extension].header
        if extension != 0:
            header.extend(h_prime, strip=False)
        header = self.add_header_info(header, mode.upper())
        header["e_input"] = (os.path.basename(fname), "Original input filename")

        if header_only:
            hdu.close()
            return header

        data = clipnflip(hdu[extension].data, header)

        if dtype is not None:
            data = data.astype(dtype)

        data = np.ma.masked_array(data, mask=mask)

        hdu.close()
        return data, header

    def add_header_info(self, header: fits.Header, mode: str, **kwargs) -> fits.Header | dict[str, Any]:
        """
        Read data from header and add it as REDUCE keyword back to the header

        Parameters
        ----------
        header : fits.Header, dict
            header to read/write info from/to
        mode : str
            instrument mode

        Returns
        -------
        header : fits.Header, dict
            header with added information
        """

        info = self.load_info()
        get = HeaderGetter(header, info, mode)

        header["e_instrument"] = get("instrument", self.name.upper())
        header["e_telescope"] = get("telescope", "")
        header["e_exptime"] = get("exposure_time", 0)

        jd = get("date")
        if jd is not None:
            jd = Time(jd, format=self.info.get("date_format", "fits"))
            jd = jd.to_value("mjd")

        header["e_orient"] = get("orientation", 0)
        # As per IDL rotate if orient is 4 or larger and transpose is undefined
        # the image is transposed
        header["e_transpose"] = get("transpose", (header["e_orient"] % 8 >= 4))

        naxis_x = get("naxis_x", 0)
        naxis_y = get("naxis_y", 0)

        prescan_x = get("prescan_x", 0)
        overscan_x = get("overscan_x", 0)
        prescan_y = get("prescan_y", 0)
        overscan_y = get("overscan_y", 0)

        header["e_xlo"] = prescan_x
        header["e_xhi"] = naxis_x - overscan_x

        header["e_ylo"] = prescan_y
        header["e_yhi"] = naxis_y - overscan_y

        header["e_gain"] = get("gain", 1)
        header["e_readn"] = get("readnoise", 0)

        header["e_sky"] = get("sky", 0)
        header["e_drk"] = get("dark", 0)
        header["e_backg"] = header["e_gain"] * (header["e_drk"] + header["e_sky"])

        header["e_imtype"] = get("image_type")
        header["e_ctg"] = get("category")

        header["e_ra"] = get("ra", 0)
        header["e_dec"] = get("dec", 0)
        header["e_jd"] = jd

        header["e_obslon"] = get("longitude")
        header["e_obslat"] = get("latitude")
        header["e_obsalt"] = get("altitude")

        if info.get("wavecal_element", None) is not None:
            header["HIERARCH e_wavecal_element"] = get(
                "wavecal_element", info.get("wavecal_element", None)
            )
        return header

    @staticmethod
    def find_files(input_dir: Path) -> list[Path]:
        """Find FITS files in the given folder

        Parameters
        ----------
        input_dir : string
            directory to look for fits and fits.gz files in, may include bash style wildcards

        Returns
        -------
        files: Iterable(Path)
            absolute path filenames
        """
        # files = glob.glob(input_dir + "/*.fits")
        # files += glob.glob(input_dir + "/*.fits.gz")
        # return list(map(Path, files))

        return list(itertools.chain(input_dir.glob("*.fits"),
                                    input_dir.glob("*.fits.gz")))

    def get_expected_values(self,
                            target: str,
                            night: datetime.date,
                            *args, **kwargs) -> dict[str, dict]:
        expectations = {
            "bias": {
                "instrument": self.info["id_instrument"],
                "night": night,
                "bias": self.info["id_bias"],
            },
            "flat": {
                "instrument": self.info["id_instrument"],
                "night": night,
                "flat": self.info["id_flat"],
            },
            "orders": {
                "instrument": self.info["id_instrument"],
                "night": night,
                "orders": self.info["id_orders"],
            },
            "scatter": {
                "instrument": self.info["id_instrument"],
                "night": night,
                "scatter": self.info["id_scatter"],
            },
            "curvature": {
                "instrument": self.info["id_instrument"],
                "night": night,
                "curvature": self.info["id_curvature"],
            },
            "wavecal_master": {
                "instrument": self.info["id_instrument"],
                "night": night,
                "wave": self.info["id_wave"],
            },
            "freq_comb_master": {
                "instrument": self.info["id_instrument"],
                "night": night,
                "comb": self.info["id_comb"],
            },
            "science": {
                "instrument": self.info["id_instrument"],
                "night": night,
                "target": target,
                "spec": self.info["id_spec"],
            },
        }

        # TODO: Compressed, DRY version of the dict above (which can be removed afterwards)
        better_expectations = {
            key: {
                "instrument": self.info["id_instrument"],
                "night": night,
                key: self.info[f"id_{key}"],
            } for key in ["bias", "flat", "orders", "scatter", "curvature"]
        } | {
            key: {
                "instrument": self.info["id_instrument"],
                "night": night,
                "target": target,
                "spec": self.info["id_spec"],
            } for key in ["science"]
        }
        return expectations

    def populate_filters(self, files: Iterable[Path]) -> dict[str, Filter]:
        """Extract values from the fits headers and store them in `self.filters`

        Parameters
        ----------
        files : list(str)
            list of fits files

        Returns
        -------
        filters: dict[str, Filter]
            list of populated filters (identical to `self.filters`)
        """
        # Empty filters
        for _, fil in self.filters.items():
            fil.clear()

        logger.debug(f"Populating filters for {c.num(len(files))} files...")

        for f in tqdm(files):
            h = fits.open(f)[0].header

            for _, fil in self.filters.items():
                fil.collect(h)

        return self.filters

    def apply_filters(self,
                      files: list[Path],
                      expected: dict[str, dict],
                      *,
                      allow_calibration_only=False):
        """
        Determine the relevant files for a given set of expected values.

        Parameters
        ----------
        files : list(files)
            list if fits files
        expected : dict
            dictionary with expected header values for each reduction step
        allow_calibration_only : bool
            TODO: what does this do?

        Returns
        -------
        files: list((dict, dict))
            list of files. The first element of each tuple is the used setting,
            and the second are the files for each step.
        """
        logger.trace(f"Filtering files")
        for file in files:
            logger.trace(f"\t{c.path(file)}")
        logger.trace(f"for expected header values\n{pprint.pformat(expected)}")

        # Fill the filters with header information
        self.populate_filters(files)

        # Use the header information determined in populate filters
        # to find potential science and calibration files in the list of files
        # result = {step : [ {setting : value}, [files] ] }
        result = {}
        for step, values in expected.items():
            result[step] = []
            data = {}
            for name, value in values.items():
                if isinstance(value, list):
                    for v in value:
                        data[name] = self.filters[name].classify(v)
                        if len(data[name]) > 0:
                            break
                else:
                    data[name] = self.filters[name].classify(value)
            # Get all combinations of possible filter values
            # e.g. if several nights are allowed
            for thingy in itertools.product(*data.values()):
                mask = np.copy(thingy[0][1])
                for i in range(1, len(thingy)):
                    mask &= thingy[i][1]
                if np.count_nonzero(mask) == 0:
                    continue
                d = {k: v[0] for k, v in zip(values.keys(), thingy)}
                f = np.array(files)[mask]
                result[step].append((d, list(f)))

        # Filter for only nights that have a science observation
        # files = [{setting: value}, {step: files}]
        files = []
        if allow_calibration_only:
            # Use all unique nights
            settings = {}
            for shared in self.shared:
                keys = [k for k in set(self.filters[shared].data) if k is not None]
                settings[shared] = keys
        else:
            # Or use only science nights
            settings = {}
            for shared in self.shared:
                keys = [key[shared] for key, _ in result[self.science]]
                settings[shared] = keys

        values = [settings[k] for k in self.shared]
        for setting in itertools.product(*values):
            setting = {k: v for k, v in zip(self.shared, setting)}
            night = setting[self.night]
            f = {}
            # For each step look for files with matching settings
            for step, step_data in result.items():
                f[step] = []
                for step_key, step_files in step_data:
                    match = [
                        setting[shared] == step_key[shared]
                        for shared in self.shared
                        if shared in step_key.keys()
                    ]
                    if all(match):
                        f[step] = step_files
                        break
                # If no matching files are found ...
                if len(f[step]) == 0:
                    if step not in self.find_closest:
                        # Show a warning
                        logger.warning(f"Could not find any files for step {c.name(step)} with settings {setting}, "
                                       f"sharing parameters {self.shared}")
                    else:
                        # Or find the closest night instead
                        j = None
                        for i, (step_key, step_files) in enumerate(step_data):
                            match = [
                                setting[shared] == step_key[shared]
                                for shared in self.shared
                                if shared in step_key.keys() and shared != self.night
                            ]
                            if all(match):
                                if j is None:
                                    j = i
                                else:
                                    diff_old = abs(step_data[j][0][self.night] - night)
                                    diff_new = abs(step_data[i][0][self.night] - night)
                                    if diff_new < diff_old:
                                        j = i
                        if j is None:
                            # We still don't find any files
                            logger.warning(f"Could not find any files for step {c.name(step)} in any night "
                                           f"with settings {setting}, sharing parameters {self.shared}")
                        else:
                            # We found files in a close night
                            closest_key, closest_files = step_data[j]
                            logger.warning(f"Using {step} files from night {night.isoformat()} "
                                           f"for observations of night {closest_key['night']}")
                            f[step] = closest_files

            if any([len(a) > 0 for a in f.values()]):
                files.append((setting, f))
        if len(files) == 0:
            logger.warning(f"No {self.science} files found matching the expected values {expected[self.science]}")

        return files

    def sort_files(self,
                   input_dir_template: str,
                   target: str,
                   night: datetime.date,
                   *args,
                   allow_calibration_only: bool = False,
                   **kwargs) -> list[dict[str, dict[str: list[Path]]]]:
        """
        Sort a set of fits files into different categories
        types are: bias, flat, wavecal, orderdef, spec

        Parameters
        ----------
        input_dir_template : str
            input directory containing the files to sort
        target : str
            name of the target as in the fits headers
        night : str
            observation night, possibly with wildcards
        mode : str
            instrument mode
            # TODO This seems to be missing from parameters
        Returns
        -------
        files_per_night : list[dict{str:dict{str:list[str]}}]
            a list of file sets, one entry per night, where each night consists of a dictionary with one entry per setting,
            each fileset has five lists of filenames: "bias", "flat", "order", "wave", "spec", organised in another dict
        nights_out : list[datetime]
            a list of observation times, same order as files_per_night
        """
        input_dir = Path(input_dir_template.format(target=target,
                                                   night=night.isoformat(),
                                                   instrument=self.name, **kwargs))
        files = self.find_files(input_dir)
        ev = self.get_expected_values(target, night, *args, **kwargs)
        files = self.apply_filters(files, ev, allow_calibration_only=allow_calibration_only)
        return files

    def get_wavecal_filename(self, header, mode, **kwargs):
        """Get the filename of the pre-existing wavelength solution for the current setting

        Parameters
        ----------
        header : fits.Header, dict
            header of the wavelength calibration file
        mode : str
            instrument mode

        Returns
        -------
        filename : str
            name of the wavelength solution file
        """

        info = self.load_info()
        specifier = header.get(info.get("wavecal_specifier", ""), "")
        instrument = "wavecal"

        return Path(__file__).parents[1] / "wavecal", f"{instrument}_{mode}_{specifier}.npz"

    def get_supported_modes(self):
        info = self.load_info()
        return info["modes"]

    def get_mask_filename(self, mode, **kwargs) -> Path:
        return Path(__file__).parents[2] / "masks" / f"mask_{self.name.lower()}_{mode.lower()}.fits.gz"

    def get_wavelength_range(self, header, mode, **kwargs):
        return self.get("wavelength_range", header, mode)


class InstrumentWithModes(Instrument):
    """
    Extends the Instrument class with observation mode
    """
    def __init__(self):
        super().__init__()

        # replacement = {k: v for k, v in zip(self.info["id_modes"], self.info["modes"])}
        self.filters["mode"] = ModeFilter(self.info["kw_modes"])
        self.shared += ["mode"]

    def get_expected_values(self, target, night, mode):
        expectations = super().get_expected_values(target, night, mode)

        id_mode = [
            self.info["id_modes"][i]
            for i, m in enumerate(self.info["modes"])
            if m == mode
        ][0]

        for key in expectations.keys():
            expectations[key]["mode"] = id_mode

        return expectations


class COMMON(Instrument):
    pass


def create_custom_instrument(name, *,
                             extension=0, info=None, mask_file=None, wavecal_file=None, has_modes=False):
    cls = Instrument if not has_modes else InstrumentWithModes

    class CUSTOM(cls):
        def __init__(self):
            super().__init__()
            self.name = name

        def load_info(self):
            if info is None:
                return COMMON().info
            try:
                with open(info) as f:
                    data = json.load(f)
                return data
            except Exception:
                return info

        def get_extension(self, header, mode):
            return extension

        def get_mask_filename(self, mode, **kwargs):
            return mask_file

        def get_wavecal_filename(self, header, mode, **kwargs):
            return wavecal_file

    return CUSTOM()
