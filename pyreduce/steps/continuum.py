import logging
import joblib

from os.path import join

from pyreduce.continuum_normalization import continuum_normalize, splice_orders
from .step import Step

logger = logging.getLogger()


class ContinuumNormalization(Step):
    """Determine the continuum to each observation"""

    def __init__(self, *args, **config):
        super().__init__(*args, **config)
        self._dependsOn += ["science", "freq_comb", "norm_flat"]
        self._loadDependsOn += ["norm_flat", "science"]

    @property
    def savefile(self):
        """str: savefile name"""
        return join(self.output_dir, self.prefix + ".cont.npz")

    def run(self, science, freq_comb, norm_flat):
        """Determine the continuum to each observation
        Also splices the orders together

        Parameters
        ----------
        science : tuple
            results from science step
        freq_comb : tuple
            results from freq_comb step (or wavecal if those don't exist)
        norm_flat : tuple
            results from the normalized flatfield step

        Returns
        -------
        heads : list(FITS header)
            FITS headers of each observation
        specs : list(array of shape (nord, ncol))
            extracted spectra
        sigmas : list(array of shape (nord, ncol))
            uncertainties of the extracted spectra
        conts : list(array of shape (nord, ncol))
            continuum for each spectrum
        columns : list(array of shape (nord, 2))
            column ranges for each spectra
        """
        wave = freq_comb
        heads, specs, sigmas, columns = science
        norm, blaze = norm_flat

        logger.info("Continuum normalization")
        conts = [None for _ in specs]
        for j, (spec, sigma) in enumerate(zip(specs, sigmas)):
            logger.info("Splicing orders")
            specs[j], wave, blaze, sigmas[j] = splice_orders(
                spec,
                wave,
                blaze,
                sigma,
                scaling=True,
                plot=self.plot,
                plot_title=self.plot_title,
            )
            logger.info("Normalizing continuum")
            conts[j] = continuum_normalize(
                specs[j],
                wave,
                blaze,
                sigmas[j],
                plot=self.plot,
                plot_title=self.plot_title,
            )

        self.save(heads, specs, sigmas, conts, columns)
        return heads, specs, sigmas, conts, columns

    def save(self, heads, specs, sigmas, conts, columns):
        """Save the results from the continuum normalization

        Parameters
        ----------
        heads : list(FITS header)
            FITS headers of each observation
        specs : list(array of shape (nord, ncol))
            extracted spectra
        sigmas : list(array of shape (nord, ncol))
            uncertainties of the extracted spectra
        conts : list(array of shape (nord, ncol))
            continuum for each spectrum
        columns : list(array of shape (nord, 2))
            column ranges for each spectra
        """
        value = {
            "heads": heads,
            "specs": specs,
            "sigmas": sigmas,
            "conts": conts,
            "columns": columns,
        }
        joblib.dump(value, self.savefile)
        logger.info("Created continuum normalization file: %s", self.savefile)

    def load(self, norm_flat, science):
        """Load the results from the continuum normalization

        Returns
        -------
        heads : list(FITS header)
            FITS headers of each observation
        specs : list(array of shape (nord, ncol))
            extracted spectra
        sigmas : list(array of shape (nord, ncol))
            uncertainties of the extracted spectra
        conts : list(array of shape (nord, ncol))
            continuum for each spectrum
        columns : list(array of shape (nord, 2))
            column ranges for each spectra
        """
        try:
            data = joblib.load(self.savefile)
            logger.info("Continuum normalization file: %s", self.savefile)
        except FileNotFoundError:
            # Use science files instead
            logger.warning(
                "No continuum normalized data found. Using unnormalized results instead."
            )
            heads, specs, sigmas, columns = science
            norm, blaze = norm_flat
            conts = [blaze for _ in specs]
            data = dict(
                heads=heads, specs=specs, sigmas=sigmas, conts=conts, columns=columns
            )
        heads = data["heads"]
        specs = data["specs"]
        sigmas = data["sigmas"]
        conts = data["conts"]
        columns = data["columns"]
        return heads, specs, sigmas, conts, columns
