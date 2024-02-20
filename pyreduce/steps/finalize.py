import logging
import os
import numpy as np
import matplotlib.pyplot as plt

import pyreduce
from pyreduce import echelle, util
from .step import Step

logger = logging.getLogger(__name__)


class Finalize(Step):
    """Create the final output files"""

    def __init__(self, *args, **config):
        super().__init__(*args, **config)
        self._depends_on += ["continuum", "freq_comb", "config"]
        self.filename = config["filename"]

    def output_file(self, number, name) -> str:
        """str: output file name"""
        out = self.filename.format(
            instrument=self.instrument.name,
            night=self.night,
            mode=self.mode,
            number=number,
            input=name,
        )
        return str(os.path.join(self.output_dir, out))

    def save_config_to_header(self, head, config, prefix="PR"):
        for key, value in config.items():
            if isinstance(value, dict):
                head = self.save_config_to_header(
                    head, value, prefix=f"{prefix} {key.upper()}"
                )
            else:
                if key in ["plot", "$schema", "__skip_existing__"]:
                    # Skip values that are not relevant to the file product
                    continue
                if value is None:
                    value = "null"
                elif not np.isscalar(value):
                    value = str(value)
                head[f"HIERARCH {prefix} {key.upper()}"] = value
        return head

    def run(self, continuum: tuple, freq_comb: tuple, config):
        """Create the final output files

        this includes:
         - heliocentric corrections
         - creating one echelle file

        Parameters
        ----------
        continuum : tuple
            results from the continuum normalization
        freq_comb : tuple
            results from the frequency comb step (or wavelength calibration)
        """
        heads, specs, sigmas, conts, columns = continuum
        wave = freq_comb

        fnames = []
        # Combine science with wavecal and continuum
        for i, (head, spec, sigma, blaze, column) in enumerate(
                zip(heads, specs, sigmas, conts, columns)
        ):
            head["e_erscle"] = ("absolute", "error scale")

            # Add heliocentric correction
            try:
                rv_corr, bjd = util.helcorr(
                    head["e_obslon"],
                    head["e_obslat"],
                    head["e_obsalt"],
                    head["e_ra"],
                    head["e_dec"],
                    head["e_jd"],
                )

                logger.debug("Heliocentric correction: %f km/s", rv_corr)
                logger.debug("Heliocentric Julian Date: %s", str(bjd))
            except KeyError:
                logger.warning("Could not calculate heliocentric correction")
                # logger.warning("Telescope is in space?")
                rv_corr = 0
                bjd = head["e_jd"]

            head["barycorr"] = rv_corr
            head["e_jd"] = bjd
            head["HIERARCH PR_version"] = pyreduce.__version__

            head = self.save_config_to_header(head, config)

            if self.plot:
                plt.plot(wave.T, (spec / blaze).T)
                if self.plot_title is not None:
                    plt.title(self.plot_title)
                plt.show()

            fname = self.save(i, head, spec, sigma, blaze, wave, column)
            fnames.append(fname)
        return fnames

    def save(self, i, head, spec, sigma, cont, wave, columns):
        """Save one output spectrum to disk

        Parameters
        ----------
        i : int
            individual number of each file
        head : FITS header
            the FITS header
        spec : array of shape (nord, ncol)
            final spectrum
        sigma : array of shape (nord, ncol)
            final uncertainties
        cont : array of shape (nord, ncol)
            final continuum scales
        wave : array of shape (nord, ncol)
            wavelength solution
        columns : array of shape (nord, 2)
            columns that carry signal

        Returns
        -------
        out_file : str
            name of the output file
        """
        original_name = os.path.splitext(head["e_input"])[0]
        out_file = self.output_file(i, original_name)
        echelle.save(
            out_file, head, spec=spec, sig=sigma, cont=cont, wave=wave, columns=columns
        )
        logger.info("Final science file: %s", out_file)
        return out_file
