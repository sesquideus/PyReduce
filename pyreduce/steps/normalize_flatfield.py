import logging
import numpy as np

from os.path import join

from .step import Step
from pyreduce.extract import extract

logger = logging.getLogger(__name__)


class NormalizeFlatField(Step):
    """Calculate the 'normalized' flat field image"""

    def __init__(self, *args, **config):
        super().__init__(*args, **config)
        self._dependsOn += ["flat", "orders", "scatter", "curvature"]

        #:{'normalize'}: Extraction method to use
        self.extraction_method = config["extraction_method"]
        if self.extraction_method == "normalize":
            #:dict: arguments for the extraction
            self.extraction_kwargs = {
                "extraction_width": config["extraction_width"],
                "lambda_sf": config["smooth_slitfunction"],
                "lambda_sp": config["smooth_spectrum"],
                "osample": config["oversampling"],
                "swath_width": config["swath_width"],
                "sigma_cutoff": config["extraction_cutoff"],
                "maxiter": config["maxiter"],
            }
        else:
            raise ValueError(
                f"Extraction method {self.extraction_method} not supported for step 'norm_flat'"
            )
        #:int: Threshold of the normalized flat field (values below this are just 1)
        self.threshold = config["threshold"]
        self.threshold_lower = config["threshold_lower"]

    @property
    def savefile(self):
        """str: Name of the blaze file"""
        return join(self.output_dir, self.prefix + ".flat_norm.npz")

    def run(self, flat, orders, scatter, curvature):
        """Calculate the 'normalized' flat field

        Parameters
        ----------
        flat : tuple(array, header)
            Master flat, and its FITS header
        orders : tuple(array, array)
            Polynomial coefficients for each order, and the first and last(+1) column containing signal

        Returns
        -------
        norm : array of shape (nrow, ncol)
            normalized flat field
        blaze : array of shape (nord, ncol)
            Continuum level as determined from the flat field for each order
        """
        flat, fhead = flat
        orders, column_range = orders
        tilt, shear = curvature

        # if threshold is smaller than 1, assume percentage value is given
        if self.threshold <= 1:
            threshold = np.percentile(flat, self.threshold * 100)
        else:
            threshold = self.threshold

        norm, _, blaze, _ = extract(
            flat,
            orders,
            gain=fhead["e_gain"],
            readnoise=fhead["e_readn"],
            dark=fhead["e_drk"],
            order_range=self.order_range,
            column_range=column_range,
            scatter=scatter,
            threshold=threshold,
            threshold_lower=self.threshold_lower,
            extraction_type=self.extraction_method,
            tilt=tilt,
            shear=shear,
            plot=self.plot,
            plot_title=self.plot_title,
            **self.extraction_kwargs,
        )

        blaze = np.ma.filled(blaze, 0)
        norm = np.nan_to_num(norm, nan=1)
        self.save(norm, blaze)
        return norm, blaze

    def save(self, norm, blaze):
        """Save normalized flat field results to disk

        Parameters
        ----------
        norm : array of shape (nrow, ncol)
            normalized flat field
        blaze : array of shape (nord, ncol)
            Continuum level as determined from the flat field for each order
        """
        np.savez(self.savefile, blaze=blaze, norm=norm)
        logger.info("Created normalized flat file: %s", self.savefile)

    def load(self):
        """Load normalized flat field results from disk

        Returns
        -------
        norm : array of shape (nrow, ncol)
            normalized flat field
        blaze : array of shape (nord, ncol)
            Continuum level as determined from the flat field for each order
        """
        try:
            data = np.load(self.savefile, allow_pickle=True)
            logger.info("Normalized flat file: %s", self.savefile)
        except FileNotFoundError:
            logger.warning(
                "No intermediate files found for the normalized flat field. Using flat = 1 instead."
            )
            data = {"blaze": None, "norm": None}
        blaze = data["blaze"]
        norm = data["norm"]
        return norm, blaze


