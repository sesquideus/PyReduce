# -*- coding: utf-8 -*-
"""
Handles instrument specific info for the NTE spectrograph

Mostly reading data from the header
"""
import logging
import os.path

from pathlib import Path

from pyreduce.instruments.common import Instrument, HeaderGetter, observation_date_to_night

logger = logging.getLogger(__name__)


class NTE(Instrument):
    def add_header_info(self, header, mode, **kwargs):
        """read data from header and add it as REDUCE keyword back to the header"""
        # "Normal" stuff is handled by the general version, specific changes to values happen here
        # alternatively you can implement all of it here, whatever works
        header = super().add_header_info(header, mode)

        header["e_ra"] /= 15
        if header["e_jd"] is not None:
            header["e_jd"] += header["e_exptime"] / (7200 * 24) + 0.5

        return header

    def get_wavecal_filename(self, header, mode, **kwargs) -> Path:
        """Get the filename of the wavelength calibration config file"""
        info = self.load_info()
        specifier = int(header[info["wavecal_specifier"]])

        cwd = os.path.dirname(__file__)
        fname = "{instrument}_{mode}_{specifier}nm_2D.npz".format(
            instrument="nte", mode=mode.lower(), specifier=specifier
        )
        fname = os.path.join(cwd, "..", "wavecal", fname)
        return Path(__file__).parents[1] / "wavecal" / f"{self.name}_{mode.lower()}_{specifier}nm_2D.npz"

    def get_wavelength_range(self, header, mode):
        wave = 7 * [7000, 20_000]
        return wave
