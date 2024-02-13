import abc
import datetime
from pathlib import Path

import pyreduce


class Workflow(metaclass=abc.ABCMeta):
    instrument: str = None
    target: str = None
    night: datetime.date = None
    mode: str = None
    steps: list = []
    order_range: tuple[int, int] = (0, 0)
    base_dir: Path = None
    input_dir: Path = None
    output_dir: Path = None

    def process(self):
        return pyreduce.reduce.main(
            self.instrument,
            self.target,
            self.night.strftime(self.night.strftime("%Y-%m-%d")), # change this
            self.mode,
            self.steps,
            base_dir=self.base_dir,
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            configuration=pyreduce.configuration.get_configuration_for_instrument(self.instrument, plot=1),
            order_range=self.order_range,
        )

