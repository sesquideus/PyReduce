import logging
import numpy as np

from tqdm import tqdm

from pyreduce import echelle, util
from .calibration import CalibrationStep
from .extraction import ExtractionStep

logger = logging.getLogger()


class ScienceExtraction(CalibrationStep, ExtractionStep):
    """Extract the science spectra"""

    def __init__(self, *args, **config):
        super().__init__(*args, **config)
        self._dependsOn += ["norm_flat", "curvature", "scatter"]
        self._loadDependsOn += ["files"]

    def science_file(self, name):
        """Name of the science file in disk, based on the input file

        Parameters
        ----------
        name : str
            name of the observation file

        Returns
        -------
        name : str
            science file name
        """
        return util.swap_extension(name, ".science.ech", path=self.output_dir)

    def run(self,
            files: list[str],
            bias: tuple,
            orders: tuple,
            norm_flat: tuple,
            curvature: tuple,
            scatter,
            mask: np.ndarray[bool]):
        """Extract Science spectra from observation

        Parameters
        ----------
        files : list(str)
            list of observations
        bias : tuple
            results from master bias step
        orders : tuple
            results from order tracing step
        norm_flat : tuple
            results from flat normalization
        curvature : tuple
            results from slit curvature step
        mask : array of shape (nrow, ncol)
            bad pixel map

        Returns
        -------
        heads : list(FITS header)
            FITS headers of each observation
        specs : list(array of shape (nord, ncol))
            extracted spectra
        sigmas : list(array of shape (nord, ncol))
            uncertainties of the extracted spectra
        columns : list(array of shape (nord, 2))
            column ranges for each spectra
        """
        heads, specs, sigmas, columns = [], [], [], []
        for fname in tqdm(files, desc="Files"):
            logger.info("Science file: %s", fname)
            # Calibrate the input image
            im, head = self.calibrate([fname], mask, bias, norm_flat)
            # Optimally extract science spectrum
            spec, sigma, _, cr = self.extract(im, head, orders, curvature, scatter=scatter)

            # save spectrum to disk
            self.save(fname, head, spec, sigma, cr)
            heads.append(head)
            specs.append(spec)
            sigmas.append(sigma)
            columns.append(cr)

        return heads, specs, sigmas, columns

    def save(self, fname, head, spec, sigma, column_range):
        """Save the results of one extraction

        Parameters
        ----------
        fname : str
            filename to save to
        head : FITS header
            FITS header
        spec : array of shape (nord, ncol)
            extracted spectrum
        sigma : array of shape (nord, ncol)
            uncertainties of the extracted spectrum
        column_range : array of shape (nord, 2)
            range of columns that have spectrum
        """
        nameout = self.science_file(fname)
        echelle.save(nameout, head, spec=spec, sig=sigma, columns=column_range)
        logger.info("Created science file: %s", nameout)

    def load(self, files):
        """Load all science spectra from disk

        Returns
        -------
        heads : list(FITS header)
            FITS headers of each observation
        specs : list(array of shape (nord, ncol))
            extracted spectra
        sigmas : list(array of shape (nord, ncol))
            uncertainties of the extracted spectra
        columns : list(array of shape (nord, 2))
            column ranges for each of the spectra
        """
        files = files["science"]
        files = [self.science_file(fname) for fname in files]

        if len(files) == 0:
            raise FileNotFoundError("Science files are required to load them")

        logger.info("Science files: %s", files)

        heads, specs, sigmas, columns = [], [], [], []
        for fname in files:
            # fname = join(self.output_dir, fname)
            science = echelle.read(
                fname,
                continuum_normalization=False,
                barycentric_correction=False,
                radial_velociy_correction=False,
            )
            heads.append(science.header)
            specs.append(science["spec"])
            sigmas.append(science["sig"])
            columns.append(science["columns"])

        return heads, specs, sigmas, columns
