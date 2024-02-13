import logging
import numpy as np
import os

from pyreduce.make_shear import Curvature as CurvatureModule
from .calibration import CalibrationStep
from .extraction import ExtractionStep

logger = logging.getLogger(__name__)


class SlitCurvatureDetermination(CalibrationStep, ExtractionStep):
    """Determine the curvature of the slit"""

    def __init__(self, *args, **config):
        super().__init__(*args, **config)

        # how many sigma of bad lines to cut away
        self.sigma_cutoff: float = config["curvature_cutoff"]
        # width of the orders in the extraction
        self.extraction_width: float = config["extraction_width"]
        # Polynomial degree of the overall fit
        self.fit_degree: int = config["degree"]
        # Orders of the curvature to fit, currently supports only 1 and 2
        self.curv_degree: int = config["curv_degree"]
        # {'1D', '2D'}: Whether to use 1d or 2d polynomials
        self.curvature_mode: str = config["dimensionality"]
        # peak finding noise threshold
        self.peak_threshold: float = config["peak_threshold"]
        # peak width
        self.peak_width: int = config["peak_width"]
        # window width to search for peak in each row
        self.window_width: float = config["window_width"]
        # Function shape that is fit to individual peaks
        self.peak_function: str = config["peak_function"]

    @property
    def savefile(self):
        """str: Name of the tilt/shear save file"""
        return os.path.join(self.output_dir, self.prefix + ".shear.npz")

    def run(self, files, orders, mask, bias):
        """Determine the curvature of the slit

        Parameters
        ----------
        files : list(str)
            files to use
        orders : tuple
            results of the order tracing
        mask : array of shape (nrow, ncol)
            Bad pixel mask

        Returns
        -------
        tilt : array of shape (nord, ncol)
            first order slit curvature at each point
        shear : array of shape (nord, ncol)
            second order slit curvature at each point
        """

        logger.info("Slit curvature files: %s", files)

        orig, thead = self.calibrate(files, mask, bias, None)
        extracted, _, _, _ = self.extract(orig, thead, orders, None)

        orders, column_range = orders
        module = CurvatureModule(
            orders,
            column_range=column_range,
            extraction_width=self.extraction_width,
            order_range=self.order_range,
            fit_degree=self.fit_degree,
            curv_degree=self.curv_degree,
            sigma_cutoff=self.sigma_cutoff,
            mode=self.curvature_mode,
            peak_threshold=self.peak_threshold,
            peak_width=self.peak_width,
            window_width=self.window_width,
            peak_function=self.peak_function,
            plot=self.plot,
            plot_title=self.plot_title,
        )
        tilt, shear = module.execute(extracted, orig)
        self.save(tilt, shear)
        return tilt, shear

    def save(self, tilt, shear):
        """Save results from the curvature

        Parameters
        ----------
        tilt : array of shape (nord, ncol)
            first order slit curvature at each point
        shear : array of shape (nord, ncol)
            second order slit curvature at each point
        """
        np.savez(self.savefile, tilt=tilt, shear=shear)
        logger.info("Created slit curvature file: %s", self.savefile)

    def load(self):
        """Load the curvature if possible, otherwise return None, None, i.e. use vertical extraction

        Returns
        -------
        tilt : array of shape (nord, ncol)
            first order slit curvature at each point
        shear : array of shape (nord, ncol)
            second order slit curvature at each point
        """
        try:
            data = np.load(self.savefile, allow_pickle=True)
            logger.info("Slit curvature file: %s", self.savefile)
        except FileNotFoundError:
            logger.warning("No data for slit curvature found, setting it to 0.")
            data = {"tilt": None, "shear": None}

        tilt = data["tilt"]
        shear = data["shear"]
        return tilt, shear
