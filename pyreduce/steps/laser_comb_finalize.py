import logging
import numpy as np

from os.path import join

from pyreduce.wavelength_calibration import WavelengthCalibrationComb
from .step import Step

logger = logging.getLogger(__name__)


class LaserFrequencyCombFinalize(Step):
    """Improve the precision of the wavelength calibration with a laser frequency comb"""

    def __init__(self, *args, **config):
        super().__init__(*args, **config)
        self._dependsOn += ["freq_comb_master", "wavecal"]
        self._loadDependsOn += ["wavecal"]

        # polynomial degree of the wavelength fit
        self.degree: tuple[int, int] = config["degree"]
        # residual threshold in m/s above which to remove lines
        self.threshold: float = config["threshold"]
        # {'1D', '2D'}: Whether to use 1D or 2D polynomials
        self.dimensionality: str = config["dimensionality"]
        self.nstep = config["nstep"]
        # Width of the peaks for finding them in the spectrum
        self.lfc_peak_width: int = config["lfc_peak_width"]

    @property
    def savefile(self):
        """str: Name of the wavelength echelle file"""
        return join(self.output_dir, self.prefix + ".comb.npz")

    def run(self, freq_comb_master, wavecal):
        """Improve the wavelength calibration with a laser frequency comb (or similar)

        Parameters
        ----------
        files : list(str)
            observation files
        wavecal : tuple()
            results from the wavelength calibration step
        orders : tuple
            results from the order tracing step
        mask : array of shape (nrow, ncol)
            Bad pixel mask

        Returns
        -------
        wave : array of shape (nord, ncol)
            improved wavelength solution
        comb : array of shape (nord, ncol)
            extracted frequency comb image
        """
        comb, chead = freq_comb_master
        wave, coef, linelist = wavecal

        module = WavelengthCalibrationComb(
            plot=self.plot,
            plot_title=self.plot_title,
            degree=self.degree,
            threshold=self.threshold,
            dimensionality=self.dimensionality,
            nstep=self.nstep,
            lfc_peak_width=self.lfc_peak_width,
        )
        wave = module.execute(comb, wave, linelist)

        self.save(wave)
        return wave

    def save(self, wave):
        """Save the results of the frequency comb improvement

        Parameters
        ----------
        wave : array of shape (nord, ncol)
            improved wavelength solution
        """
        np.savez(self.savefile, wave=wave)
        logger.info("Created frequency comb wavecal file: %s", self.savefile)

    def load(self, wavecal):
        """Load the results of the frequency comb improvement if possible,
        otherwise just use the normal wavelength solution

        Parameters
        ----------
        wavecal : tuple
            results from the wavelength calibration step

        Returns
        -------
        wave : array of shape (nord, ncol)
            improved wavelength solution
        comb : array of shape (nord, ncol)
            extracted frequency comb image
        """
        try:
            data = np.load(self.savefile, allow_pickle=True)
            logger.info("Frequency comb wavecal file: %s", self.savefile)
        except FileNotFoundError:
            logger.warning("No data for Laser Frequency Comb found, using regular wavelength calibration instead")
            wave, coef, linelist = wavecal
            data = {"wave": wave}
        wave = data["wave"]
        return wave
