import logging

from .step import Step
from .. import colour as c

logger = logging.getLogger(__name__)


class Mask(Step):
    """Load the bad pixel mask for the given instrument/mode"""

    def __init__(self, *args, **config):
        super().__init__(*args, **config)

    def run(self):
        """Load the mask file from disk

        Returns
        -------
        mask : array of shape (nrow, ncol)
            Bad pixel mask for this setting
        """
        return self.load()

    def load(self):
        """Load the mask file from disk

        Returns
        -------
        mask : array of shape (nrow, ncol)
            Bad pixel mask for this setting
        """
        mask_file = self.instrument.get_mask_filename(mode=self.mode)
        try:
            mask, _ = self.instrument.load_fits(mask_file, self.mode, extension=0)
            mask = ~mask.data.astype(bool)  # REDUCE mask are inverse to numpy masks
            logger.info(f"Loaded a bad pixel mask file {c.path(mask_file)}")
        except (FileNotFoundError, ValueError):
            logger.error(f"Bad pixel mask datafile {c.path(mask_file)} not found. Using all pixels instead.")
            mask = False
        return mask
