import abc

from pyreduce.extract import extract
from .step import Step


class ExtractionStep(Step, metaclass=abc.ABCMeta):
    def __init__(self, *args, **config):
        super().__init__(*args, **config)
        self._dependsOn += [
            "orders",
        ]

        #:{'arc', 'optimal'}: Extraction method to use
        self.extraction_method = config["extraction_method"]
        if self.extraction_method == "arc":
            #:dict: arguments for the extraction
            self.extraction_kwargs = {
                "extraction_width": config["extraction_width"],
                "sigma_cutoff": config["extraction_cutoff"],
                "collapse_function": config["collapse_function"],
            }
        elif self.extraction_method == "optimal":
            self.extraction_kwargs = {
                "extraction_width": config["extraction_width"],
                "lambda_sf": config["smooth_slitfunction"],
                "lambda_sp": config["smooth_spectrum"],
                "osample": config["oversampling"],
                "swath_width": config["swath_width"],
                "sigma_cutoff": config["extraction_cutoff"],
                "maxiter": config["maxiter"],
            }
        else:
            raise ValueError(
                f"Extraction method {self.extraction_method} not supported for step 'wavecal'"
            )

    def extract(self, img, head, orders, curvature, scatter=None):
        orders, column_range = orders if orders is not None else (None, None)
        tilt, shear = curvature if curvature is not None else (None, None)

        data, unc, blaze, cr = extract(
            img,
            orders,
            gain=head["e_gain"],
            readnoise=head["e_readn"],
            dark=head["e_drk"],
            column_range=column_range,
            extraction_type=self.extraction_method,
            order_range=self.order_range,
            plot=self.plot,
            plot_title=self.plot_title,
            tilt=tilt,
            shear=shear,
            scatter=scatter,
            **self.extraction_kwargs,
        )
        return data, unc, blaze, cr

