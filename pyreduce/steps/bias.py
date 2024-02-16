import logging
import pprint
import numpy as np
import os

from astropy.io import fits
from pathlib import Path

from pyreduce.combine_frames import combine_bias, combine_polynomial
from .step import Step

logger = logging.getLogger()


class Bias(Step):
    """Calculates the master bias"""

    def __init__(self, *args, **config):
        super().__init__(*args, **config)
        self._dependsOn += ["mask"]
        self._loadDependsOn += ["mask"]

        # polynomial degree of the fit between exposure time and pixel values
        self.degree: int = config["degree"]

    @property
    def savefile(self):
        """str: Name of master bias fits file"""
        return os.path.join(self.output_dir, self.prefix + ".bias.fits")

    def run(self, files: list[Path], mask):
        """Calculate the master bias

        Parameters
        ----------
        files : list(str)
            bias files
        mask : array of shape (nrow, ncol)
            bad pixel map

        Returns
        -------
        bias : masked array of shape (nrow, ncol)
            master bias data, with the bad pixel mask applied
        bhead : FITS header
            header of the master bias
        """
        logger.info(f"Running {self.__class__.__name__} step with files\n{pprint.pformat(files)}")

        if self.degree == 0:
            # If the degree is 0, we just combine all images into a single master bias
            # this works great if we assume there is no dark at exposure time 0
            bias, bhead = combine_bias(
                files,
                self.instrument,
                self.mode,
                mask=mask,
                plot=self.plot,
                plot_title=self.plot_title,
            )
        else:
            # Otherwise we fit a polynomial to each pixel in the image, with
            # the pixel value versus the exposure time. The constant coefficients
            # are then the bias, and the others are used to scale with the
            # exposure time
            bias, bhead = combine_polynomial(
                files,
                self.instrument,
                self.mode,
                mask=mask,
                degree=self.degree,
                plot=self.plot,
                plot_title=self.plot_title,
            )

        self.save(bias.data, bhead)
        return bias, bhead

    def save(self, bias, bhead):
        """Save the master bias to a FITS file

        Parameters
        ----------
        bias : array of shape (nrow, ncol)
            bias data
        bhead : FITS header
            bias header
        """
        bias = np.asarray(bias, dtype=np.float32)

        if self.degree == 0:
            hdus = fits.PrimaryHDU(data=bias, header=bhead)
        else:
            hdus = [fits.PrimaryHDU(data=bias[0], header=bhead)]
            for i in range(1, len(bias)):
                hdus += [fits.ImageHDU(data=bias[i])]
            hdus = fits.HDUList(hdus)

        hdus.writeto(
            self.savefile,
            overwrite=True,
            output_verify="silentfix+ignore",
        )
        logger.info("Created master bias file: %s", self.savefile)

    def load(self, mask):
        """Load the master bias from a previous run

        Parameters
        ----------
        mask : array of shape (nrow, ncol)
            Bad pixel mask

        Returns
        -------
        bias : masked array of shape (nrow, ncol)
            master bias data, with the bad pixel mask applied
        bhead : FITS header
            header of the master bias
        """
        try:
            logger.info("Master bias file: %s", self.savefile)
            hdu = fits.open(self.savefile)
            degree = len(hdu) - 1
            if degree == 0:
                bias, bhead = hdu[0].data, hdu[0].header
                bias = np.ma.masked_array(bias, mask=mask)
            else:
                bhead = hdu[0].header
                bias = np.array([h.data for h in hdu])
                bias = np.ma.masked_array(bias, mask=[mask for _ in range(len(hdu))])
        except FileNotFoundError:
            logger.warning("No intermediate bias file found. Using Bias = 0 instead.")
            bias, bhead = None, None
        return bias, bhead
