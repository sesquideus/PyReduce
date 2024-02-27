import logging
import numpy as np

from pathlib import Path

from .calibration import CalibrationStep
from pyreduce.estimate_background_scatter import estimate_background_scatter

logger = logging.getLogger(__name__)


class BackgroundScatter(CalibrationStep):
    """Determine the background scatter"""

    def __init__(self, *args, **config):
        super().__init__(*args, **config)
        self._depends_on += ["orders"]

        # Polynomial degrees for the background scatter fit, in row, column direction
        self.scatter_degree: int | tuple[int, int] = config["scatter_degree"]
        self.extraction_width = config["extraction_width"]
        self.sigma_cutoff = config["scatter_cutoff"]
        self.border_width = config["border_width"]

    @property
    def savefile(self) -> Path:
        """str: Name of the scatter file"""
        return self.output_dir / f"{self.prefix}.scatter.npz"

    def run(self, files, mask, bias, orders):
        logger.info("Background scatter files: %s", files)

        scatter_img, shead = self.calibrate(files, mask, bias)

        orders, column_range = orders
        scatter = estimate_background_scatter(
            scatter_img,
            orders,
            column_range=column_range,
            extraction_width=self.extraction_width,
            scatter_degree=self.scatter_degree,
            sigma_cutoff=self.sigma_cutoff,
            border_width=self.border_width,
            plot=self.plot,
            plot_title=self.plot_title,
        )

        self.save(scatter)
        return scatter

    def save(self, scatter):
        """Save scatter results to disk

        Parameters
        ----------
        scatter : array
            scatter coefficients
        """
        np.savez(self.savefile, scatter=scatter)
        logger.info("Created background scatter file: %s", self.savefile)

    def load(self):
        """Load scatter results from disk

        Returns
        -------
        scatter : array
            scatter coefficients
        """
        try:
            data = np.load(self.savefile, allow_pickle=True)
            logger.info(f"Background scatter file {self.savefile}")
        except FileNotFoundError:
            logger.warning("No intermediate files found for the scatter. Using scatter = 0 instead.")
            data = {"scatter": None}
        scatter = data["scatter"]
        return scatter


