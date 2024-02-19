import logging

from .step import Step

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
            logger.info("Bad pixel mask file: %s", mask_file)
        except (FileNotFoundError, ValueError):
            logger.error(
                "Bad Pixel Mask datafile %s not found. Using all pixels instead.",
                mask_file,
            )
            mask = False
        return mask
