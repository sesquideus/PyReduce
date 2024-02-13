import logging
import os

from pyreduce.wavelength_calibration import LineList
from pyreduce.wavelength_calibration import WavelengthCalibrationInitialize as WavelengthCalibrationInitializeModule
from .step import Step

logger = logging.getLogger(__name__)


class WavelengthCalibrationInitialize(Step):
    """Create the initial wavelength solution file"""

    def __init__(self, *args, **config):
        super().__init__(*args, **config)
        self._dependsOn += ["wavecal_master"]
        self._loadDependsOn += ["config", "wavecal_master"]

        # Polynomial degree of the wavelength calibration in order, column direction
        self.degree: tuple[int, int] = config["degree"]
        # Wavelength range around the initial guess to explore
        self.wave_delta: float = config["wave_delta"]
        # Number of walkers in the MCMC
        self.nwalkers: int = config["nwalkers"]
        # Number of steps in the MCMC
        self.steps: int = config["steps"]
        # Resiudal range to accept as match between peaks and atlas in m/s
        self.resid_delta: float = config["resid_delta"]
        # Element for the atlas to use
        self.element: str = config["element"]
        # Medium the medium of the instrument, air or vac
        self.medium: str = config["medium"]
        # Gaussian smoothing parameter applied to the observed spectrum in pixel scale, set to 0 to disable smoothing
        self.smoothing: float = config["smoothing"]
        # Minimum height of spectral lines in the normalized spectrum.
        # Values of 1 and above are interpreted as percentiles of the spectrum, set to 0 to disable the cutoff
        self.cutoff: float = config["cutoff"]

    @property
    def savefile(self):
        """str: Name of the wavelength echelle file"""
        return os.path.join(self.output_dir, self.prefix + ".linelist.npz")

    def run(self, wavecal_master):
        thar, thead = wavecal_master

        # Get the initial wavelength guess from the instrument
        wave_range = self.instrument.get_wavelength_range(thead, self.mode)
        if wave_range is None:
            raise ValueError(
                "This instrument is missing an initial wavelength guess for wavecal_init"
            )

        module = WavelengthCalibrationInitializeModule(
            plot=self.plot,
            plot_title=self.plot_title,
            degree=self.degree,
            wave_delta=self.wave_delta,
            nwalkers=self.nwalkers,
            steps=self.steps,
            resid_delta=self.resid_delta,
            element=self.element,
            medium=self.medium,
            smoothing=self.smoothing,
            cutoff=self.cutoff,
        )
        linelist = module.execute(thar, wave_range)
        self.save(linelist)
        return linelist

    def save(self, linelist):
        linelist.save(self.savefile)
        logger.info("Created wavelength calibration linelist file: %s", self.savefile)

    def load(self, config, wavecal_master):
        thar, thead = wavecal_master
        try:
            # Try loading the custom reference file
            reference = self.savefile
            linelist = LineList.load(reference)
        except FileNotFoundError:
            # If that fails, load the file provided by PyReduce
            # It usually fails because we want to use this one
            reference = self.instrument.get_wavecal_filename(
                thead, self.mode, **config["instrument"]
            )

            # This should fail if there is no provided file by PyReduce
            linelist = LineList.load(reference)
        logger.info("Wavelength calibration linelist file: %s", reference)
        return linelist
