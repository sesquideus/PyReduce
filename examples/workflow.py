import abc
import argparse
import datetime
import logging
import typing

from pathlib import Path

import pyreduce

logger = logging.getLogger(__name__)


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
    dataset_class: typing.ClassVar = None
    local_dir: Path = Path("~/astar/pyreduce/data/").expanduser()
    base_dir_template: str = None
    input_dir_template: str = None
    output_dir_template: str = None
    debug: bool = False

    def __init__(self):
        self.argparser = argparse.ArgumentParser()
        self.argparser.add_argument("-d", "--debug", action="store_true")
        self.add_arguments()
        self.args = self.argparser.parse_args()

        self.configuration = None
        self.base_dir_template = str(self.dataset_class(local_dir_template=self.local_dir).data_dir)

        self.debug = self.args.debug
        logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        if self.debug:
            logger.warning(f"Workflow {self.__class__.__name__} running in debug mode")

    def add_arguments(self) -> None:
        """ Hook for adding more arguments in derived workflows """
        pass

    def override_configuration(self, **kwargs):
        """ Hook for overriding the configuration in derived workflows """
        pass

    def process(self):
        self.configuration = pyreduce.configuration.get_configuration_for_instrument(self.instrument, plot=1)
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
