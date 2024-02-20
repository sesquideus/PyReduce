import logging
import numpy as np

from os.path import join
from astropy.io import fits

from .calibration import CalibrationStep
from .extraction import ExtractionStep

logger = logging.getLogger(__name__)


class LaserFrequencyCombMaster(CalibrationStep, ExtractionStep):
    """Create a laser frequency comb (or similar) master image"""

    def __init__(self, *args, **config):
        super().__init__(*args, **config)
        self._depends_on += ["norm_flat", "curvature"]

    @property
    def savefile(self):
        """str: Name of the wavelength echelle file"""
        return join(self.output_dir, self.prefix + ".comb_master.fits")

    def run(self, files, orders, mask, curvature, bias, norm_flat):
        """Improve the wavelength calibration with a laser frequency comb (or similar)

        Parameters
        ----------
        files : list(str)
            observation files
        orders : tuple
            results from the order tracing step
        mask : array of shape (nrow, ncol)
            Bad pixel mask
        curvature : tuple
            results from the curvature step
        bias : tuple
            results from the bias step

        Returns
        -------
        comb : array of shape (nord, ncol)
            extracted frequency comb image
        chead : Header
            FITS header of the combined image
        """

        if len(files) == 0:
            raise FileNotFoundError("No files for Laser Frequency Comb found")
        logger.info("Frequency comb files: %s", files)

        # Combine the input files and calibrate
        orig, chead = self.calibrate(files, mask, bias, norm_flat)
        # Extract the spectrum
        comb, _, _, _ = self.extract(orig, chead, orders, curvature)
        self.save(comb, chead)
        return comb, chead

    def save(self, comb, chead):
        """Save the master comb to a FITS file

        Parameters
        ----------
        comb : array of shape (nrow, ncol)
            master comb data
        chead : FITS header
            master comb header
        """
        comb = np.asarray(comb, dtype=np.float64)
        fits.writeto(
            self.savefile,
            data=comb,
            header=chead,
            overwrite=True,
            output_verify="silentfix+ignore",
        )
        logger.info("Created frequency comb master spectrum: %s", self.savefile)

    def load(self):
        """Load master comb from disk

        Returns
        -------
        comb : masked array of shape (nrow, ncol)
            Master comb with bad pixel map applied
        chead : FITS header
            Master comb FITS header
        """
        comb = fits.open(self.savefile)[0]
        comb, chead = comb.data, comb.header
        logger.info(f"Frequency comb master spectrum: {self.savefile}")
        return comb, chead
