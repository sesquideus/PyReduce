import logging
import numpy as np

from pathlib import Path

from pyreduce.trace_orders import mark_orders
from .calibration import CalibrationStep


logger = logging.getLogger(__name__)


class OrderTracing(CalibrationStep):
    """Determine the polynomial fits describing the pixel locations of each order"""

    def __init__(self, *args, **config):
        super().__init__(*args, **config)

        # Minimum size of each cluster to be included in further processing
        self.min_cluster: int = config["min_cluster"]
        # Minimum width of each cluster after mergin
        self.min_width: int | float = config["min_width"]
        # Size of the gaussian filter for smoothing
        self.filter_size: int = config["filter_size"]
        # Background noise value threshold
        self.noise: int = config["noise"]
        # Polynomial degree of the fit to each order
        self.fit_degree: int = config["degree"]

        self.degree_before_merge = config["degree_before_merge"]
        self.regularization = config["regularization"]
        self.closing_shape = config["closing_shape"]
        self.auto_merge_threshold = config["auto_merge_threshold"]
        self.merge_min_threshold = config["merge_min_threshold"]
        self.sigma = config["split_sigma"]
        # Number of pixels at the edge of the detector to ignore
        self.border_width: int = config["border_width"]
        # Whether to use manual alignment
        self.manual: bool = config["manual"]

    @property
    def savefile(self) -> Path:
        """str: Name of the order tracing file"""
        return Path(self.output_dir) / f"{self.prefix}.ord_default.npz"

    def run(self, files, mask, bias):
        """Determine polynomial coefficients describing order locations

        Parameters
        ----------
        files : list(str)
            Observation used for order tracing (should only have one element)
        mask : array of shape (nrow, ncol)
            Bad pixel mask

        Returns
        -------
        orders : array of shape (nord, ndegree+1)
            polynomial coefficients for each order
        column_range : array of shape (nord, 2)
            first and last(+1) column that carries signal in each order
        """

        logger.info("Order tracing files: %s", files)

        order_img, ohead = self.calibrate(files, mask, bias, None)

        orders, column_range = mark_orders(
            order_img,
            min_cluster=self.min_cluster,
            min_width=self.min_width,
            filter_size=self.filter_size,
            noise=self.noise,
            opower=self.fit_degree,
            degree_before_merge=self.degree_before_merge,
            regularization=self.regularization,
            closing_shape=self.closing_shape,
            border_width=self.border_width,
            manual=self.manual,
            auto_merge_threshold=self.auto_merge_threshold,
            merge_min_threshold=self.merge_min_threshold,
            sigma=self.sigma,
            plot=self.plot,
            plot_title=self.plot_title,
        )

        self.save(orders, column_range)

        return orders, column_range

    def save(self, orders, column_range):
        """Save order tracing results to disk

        Parameters
        ----------
        orders : array of shape (nord, ndegree+1)
            polynomial coefficients
        column_range : array of shape (nord, 2)
            first and last(+1) column that carry signal in each order
        """
        np.savez(self.savefile, orders=orders, column_range=column_range)
        logger.info("Created order tracing file: %s", self.savefile)

    def load(self):
        """Load order tracing results

        Returns
        -------
        orders : array of shape (nord, ndegree+1)
            polynomial coefficients for each order
        column_range : array of shape (nord, 2)
            first and last(+1) column that carries signal in each order
        """
        logger.info(f"Order tracing file '{self.savefile}'")
        data = np.load(self.savefile, allow_pickle=True)
        orders = data["orders"]
        column_range = data["column_range"]
        return orders, column_range


