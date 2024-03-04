import logging
import numpy as np
import os

from astropy.io import fits

from pyreduce import colour as c
from .calibration import CalibrationStep
from .extraction import ExtractionStep

logger = logging.getLogger(__name__)


class WavelengthCalibrationMaster(CalibrationStep, ExtractionStep):
    """Create wavelength calibration master image"""

    def __init__(self, *args, **config):
        super().__init__(*args, **config)
        self._depends_on += ["norm_flat", "curvature"]

    @property
    def savefile(self):
        """str: Name of the wavelength echelle file"""
        return os.path.join(self.output_dir, self.prefix + ".thar_master.fits")

    def run(self, files, orders, mask, curvature, bias, norm_flat):
        """Perform wavelength calibration

        This consists of extracting the wavelength image and fitting a polynomial to the known spectral lines

        Parameters
        ----------
        files : list(str)
            wavelength calibration files
        orders : tuple(array, array)
            Polynomial coefficients of each order, and columns with signal of each order
        mask : array of shape (nrow, ncol)
            Bad pixel mask

        Returns
        -------
        wave : array of shape (nord, ncol)
            wavelength for each point in the spectrum
        thar : array of shape (nrow, ncol)
            extracted wavelength calibration image
        coef : array of shape (*ndegrees,)
            polynomial coefficients of the wavelength fit
        linelist : record array of shape (nlines,)
            Updated line information for all lines
        """
        if len(files) == 0:
            raise FileNotFoundError("No files found for wavelength calibration")
        logger.info("Wavelength calibration files: %s", files)
        # Load wavecal image
        orig, thead = self.calibrate(files, mask, bias, norm_flat)
        # Extract wavecal spectrum
        thar, _, _, _ = self.extract(orig, thead, orders, curvature)
        self.save(thar, thead)
        return thar, thead

    def save(self, thar, thead):
        """Save the master wavelength calibration to a FITS file

        Parameters
        ----------
        thar : array of shape (nrow, ncol)
            master flat data
        thead : FITS header
            master flat header
        """
        thar = np.asarray(thar, dtype=np.float64)
        fits.writeto(
            self.savefile,
            data=thar,
            header=thead,
            overwrite=True,
            output_verify="silentfix+ignore",
        )
        logger.info(f"Created wavelength calibration spectrum file {c.path(self.savefile)}")

    def load(self):
        """Load master wavelength calibration from disk

        Returns
        -------
        thar : masked array of shape (nrow, ncol)
            Master wavecal with bad pixel map applied
        thead : FITS header
            Master wavecal FITS header
        """
        thar = fits.open(self.savefile)[0]
        thar, thead = thar.data, thar.header
        logger.info("Wavelength calibration spectrum file: %s", self.savefile)
        return thar, thead


