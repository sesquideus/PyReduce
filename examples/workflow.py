import abc
import datetime
from pathlib import Path

import pyreduce


class Workflow(metaclass=abc.ABCMeta):
    """
    Abstract base class for all workflows
    """
    instrument: str = None
    target: str = None
    night: datetime.date = None
    mode: str = None
    steps: list = []
    order_range: tuple[int, int] = (0, 0)
    base_dir_template: str | Path = None
    input_dir_template: str | Path = None
    output_dir_template: str | Path = None
    debug: bool = False

    def __init__(self):
        self.configuration = None

    def override_configuration(self, **kwargs):
        pass

    def process(self):
        self.configuration = pyreduce.configuration.get_configuration_for_instrument(self.instrument, plot=1),
        self.override_configuration()

        return pyreduce.reduce.main(
            self.instrument,
            self.target,
            self.night,
            self.mode,
            steps=self.steps,
            base_dir_template=self.base_dir_template,
            input_dir_template=self.input_dir_template,
            output_dir_template=self.output_dir_template,
            configuration=self.configuration,
            order_range=self.order_range,
            debug=self.debug,
        )

