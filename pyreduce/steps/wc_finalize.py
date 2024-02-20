import logging
import numpy as np
import os

from pyreduce.wavelength_calibration import WavelengthCalibration as WavelengthCalibrationModule
from .step import Step

logger = logging.getLogger(__name__)


class WavelengthCalibrationFinalize(Step):
    """Perform wavelength calibration"""

    def __init__(self, *args, **config):
        super().__init__(*args, **config)
        self._depends_on += ["wavecal_master", "wavecal_init"]

        # Polynomial degree of the wavelength calibration in order, column direction
        self.degree: tuple[int, int] = config["degree"]
        # Whether to use manual alignment instead of cross correlation
        self.manual: bool = config["manual"]
        # residual threshold in m/s
        self.threshold: float = config["threshold"]
        # Number of iterations in the remove lines, auto id cycle
        self.iterations: int = config["iterations"]
        # {'1D', '2D'}: Whether to use 1d or 2d polynomials
        # TODO: Change this to int
        self.dimensionality: str = config["dimensionality"]
        # Number of detector offset steps, due to detector design
        self.nstep: int = config["nstep"]
        # How many columns to use in the 2D cross correlation alignment. 0 means all pixels (slow).
        self.correlate_cols: int = config['correlate_cols']
        # fraction of columns, to allow individual orders to shift
        self.shift_window: float = config["shift_window"]
        # elements of the spectral lamp
        self.element: str = config["element"]
        # medium of the detector, vac or air
        self.medium: str = config["medium"]

    @property
    def savefile(self):
        """str: Name of the wavelength echelle file"""
        return os.path.join(self.output_dir, self.prefix + ".thar.npz")

    def run(self, wavecal_master, wavecal_init):
        """Perform wavelength calibration

        This consists of extracting the wavelength image
        and fitting a polynomial the known spectral lines

        Parameters
        ----------
        wavecal_master : tuple
            results of the wavecal_master step, containing the master wavecal image
            and its header
        wavecal_init : LineList
            the initial LineList guess with the positions and wavelengths of lines

        Returns
        -------
        wave : array of shape (nord, ncol)
            wavelength for each point in the spectrum
        coef : array of shape (*ndegrees,)
            polynomial coefficients of the wavelength fit
        linelist : record array of shape (nlines,)
            Updated line information for all lines
        """
        thar, thead = wavecal_master
        linelist = wavecal_init

        module = WavelengthCalibrationModule(
            plot=self.plot,
            plot_title=self.plot_title,
            manual=self.manual,
            degree=self.degree,
            threshold=self.threshold,
            iterations=self.iterations,
            dimensionality=self.dimensionality,
            nstep=self.nstep,
            correlate_cols=self.correlate_cols,
            shift_window=self.shift_window,
            element=self.element,
            medium=self.medium,
        )
        wave, coef = module.execute(thar, linelist)
        self.save(wave, coef, linelist)
        return wave, coef, linelist

    def save(self, wave, coef, linelist):
        """Save the results of the wavelength calibration

        Parameters
        ----------
        wave : array of shape (nord, ncol)
            wavelength for each point in the spectrum
        coef : array of shape (ndegrees,)
            polynomial coefficients of the wavelength fit
        linelist : record array of shape (nlines,)
            Updated line information for all lines
        """
        np.savez(self.savefile, wave=wave, coef=coef, linelist=linelist)
        logger.info("Created wavelength calibration file: %s", self.savefile)

    def load(self):
        """Load the results of the wavelength calibration

        Returns
        -------
        wave : array of shape (nord, ncol)
            wavelength for each point in the spectrum
        coef : array of shape (*ndegrees,)
            polynomial coefficients of the wavelength fit
        linelist : record array of shape (nlines,)
            Updated line information for all lines
        """
        data = np.load(self.savefile, allow_pickle=True)
        logger.info("Wavelength calibration file: %s", self.savefile)
        wave = data["wave"]
        coef = data["coef"]
        linelist = data["linelist"]
        return wave, coef, linelist
