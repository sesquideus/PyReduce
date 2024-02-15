import logging
import numpy as np

from astropy.io import fits
from os.path import join

from .calibration import CalibrationStep

logger = logging.getLogger()


class Flat(CalibrationStep):
    """Calculates the master flat"""

    def __init__(self, *args, **config):
        super().__init__(*args, **config)
        self._loadDependsOn += ["mask"]

    @property
    def savefile(self):
        """str: Name of master bias fits file"""
        return join(self.output_dir, self.prefix + ".flat.fits")

    def save(self, flat, fhead):
        """Save the master flat to a FITS file

        Parameters
        ----------
        flat : array of shape (nrow, ncol)
            master flat data
        fhead : FITS header
            master flat header
        """
        flat = np.asarray(flat, dtype=np.float32)
        fits.writeto(
            self.savefile,
            data=flat,
            header=fhead,
            overwrite=True,
            output_verify="silentfix+ignore",
        )
        logger.info("Created master flat file: %s", self.savefile)

    def run(self, files, bias, mask):
        """Calculate the master flat, with the bias already subtracted

        Parameters
        ----------
        files : list(str)
            flat files
        bias : tuple(array of shape (nrow, ncol), FITS header)
            master bias and header
        mask : array of shape (nrow, ncol)
            Bad pixel mask

        Returns
        -------
        flat : masked array of shape (nrow, ncol)
            Master flat with bad pixel map applied
        fhead : FITS header
            Master flat FITS header
        """
        logger.info("Flat files: %s", files)
        # This is just the calibration of images
        flat, fhead = self.calibrate(files, mask, bias, None)
        # And then save it
        self.save(flat.data, fhead)
        return flat, fhead

    def load(self, mask):
        """Load master flat from disk

        Parameters
        ----------
        mask : array of shape (nrow, ncol)
            Bad pixel mask

        Returns
        -------
        flat : masked array of shape (nrow, ncol)
            Master flat with bad pixel map applied
        fhead : FITS header
            Master flat FITS header
        """
        try:
            flat = fits.open(self.savefile)[0]
            flat, fhead = flat.data, flat.header
            flat = np.ma.masked_array(flat, mask=mask)
            logger.info("Master flat file: %s", self.savefile)
        except FileNotFoundError:
            logger.warning(
                "No intermediate file for the flat field found. Using Flat = 1 instead"
            )
            flat, fhead = None, None
        return flat, fhead
