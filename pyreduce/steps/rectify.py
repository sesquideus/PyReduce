from astropy.io import fits
from tqdm import tqdm

from pyreduce import util
from pyreduce.rectify import merge_images, rectify_image

from .step import Step


class RectifyImage(Step):
    """ Create a 2D image of the rectified orders """

    def __init__(self, *args, **config):
        super().__init__(*args, **config)
        self._dependsOn += ["files", "orders", "curvature", "mask", "freq_comb"]
        # self._loadDependsOn += []

        self.extraction_width = config["extraction_width"]
        self.input_files = config["input_files"]

    def filename(self, name):
        return util.swap_extension(name, ".rectify.fits", path=self.output_dir)

    def run(self, files, orders, curvature, mask, freq_comb):
        orders, column_range = orders
        tilt, shear = curvature
        wave = freq_comb

        files = files[self.input_files]

        rectified = {}
        for fname in tqdm(files, desc="Files"):
            img, head = self.instrument.load_fits(
                fname, self.mode, mask=mask, dtype="f8"
            )

            images, cr, xwd = rectify_image(
                img,
                orders,
                column_range,
                self.extraction_width,
                self.order_range,
                tilt,
                shear,
            )
            wavelength, image = merge_images(images, wave, cr, xwd)

            self.save(fname, image, wavelength, header=head)
            rectified[fname] = (wavelength, image)

        return rectified

    def save(self, fname, image, wavelength, header=None):
        # Change filename
        fname = self.filename(fname)
        # Create HDU List, one extension per order
        primary = fits.PrimaryHDU(header=header)
        secondary = fits.ImageHDU(data=image)
        column = fits.Column(name="wavelength", array=wavelength, format="D")
        tertiary = fits.BinTableHDU.from_columns([column])
        hdus = fits.HDUList([primary, secondary, tertiary])
        # Save data to file
        hdus.writeto(fname, overwrite=True, output_verify="silentfix")

    def load(self, files):
        files = files[self.input_files]

        rectified = {}
        for orig_fname in files:
            fname = self.filename(orig_fname)
            data = fits.open(fname)
            img = data[1].data
            wave = data[2].data["wavelength"]
            rectified[orig_fname] = (wave, img)

        return rectified
