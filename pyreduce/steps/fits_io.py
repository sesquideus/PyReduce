import abc
import logging
import numpy as np

from astropy.io import fits

from .step import Step

logger = logging.getLogger(__name__)


class FitsIOStep(Step, metaclass=abc.ABCMeta):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loadDependsOn += ["mask"]
        self.allow_failure = True

    def save(self, data: np.ndarray, head, dtype=None) -> None:
        """
        Save the data to a FITS file

        Parameters
        ----------
        data : array of shape (nrow, ncol)
            bias data
        head : FITS header
            bias header
        """
        if dtype is not None:
            data = np.asarray(data, dtype=np.float32)

        fits.writeto(
            self.savefile,
            data=data,
            header=head,
            overwrite=True,
            output_verify="silentfix+ignore",
        )
        logger.info("Created data file: %s", self.savefile)

    def load(self, mask):
        """
        Load the master bias from a previous run

        Parameters
        ----------
        mask : array of shape (nrow, ncol)
            Bad pixel mask

        Returns
        -------
        data : masked array of shape (nrow, ncol)
            master bias data, with the bad pixel mask applied
        head : FITS header
            header of the master bias
        """
        try:
            data = fits.open(self.savefile)[0]
            data, head = data.data, data.header
            data = np.ma.masked_array(data, mask=mask)
            logger.info("Data file: %s", self.savefile)
        except FileNotFoundError as ex:
            if self.allow_failure:
                logger.warning("No data file found")
                data, head = None, None
            else:
                raise ex
        return data, head
