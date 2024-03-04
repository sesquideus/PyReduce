import abc
import argparse
import datetime
import logging

from pathlib import Path

import pyreduce
from pyreduce.datasets import Dataset
from pyreduce import colour as c

logger = logging.getLogger('pyreduce')


class Workflow(metaclass=abc.ABCMeta):
    """
    Abstract base class for all workflows
    """
    instrument_name: str = None
    target: str = None
    night: datetime.date = None
    mode: str = None
    steps: list = []
    order_range: tuple[int, int] = (0, 0)
    dataset: Dataset = None
    # Default path for downloading and processing datasets
    local_dir: Path = Path("~/astar/pyreduce/data/").expanduser()
    base_dir_template: str = None
    input_dir_template: str = None
    output_dir_template: str = None
    # URL to retrieve the data from
    data_url: str = None
    debug: bool = False

    def __init__(self):
        self.argparser = argparse.ArgumentParser()
        self.argparser.add_argument("-d", "--debug", action="store_true",
                                    help="Enable debug output")
        self.argparser.add_argument("-t", "--trace", action="store_true",
                                    help="Enable extra verbose debug output")
        self.argparser.add_argument("-p", "--plot", action="store_true",
                                    help="Enable interactive plotting (currently not working)")
        self.add_arguments()
        self.args = self.argparser.parse_args()
        self.debug = self.args.debug
        self.trace = self.args.trace
        self.plot = self.args.plot

        logger.setLevel(logging.INFO)
        if self.debug:
            logger.setLevel(logging.DEBUG)
            logger.warning(f"Workflow {c.name(self.__class__.__name__)} running in debug mode")
        if self.trace:
            logger.setLevel(logging.TRACE)
            logger.warning(f"Workflow {c.name(self.__class__.__name__)} running in tracing mode, expect lots of output")

        self.configuration = None
        self.dataset = Dataset(instrument_name=self.instrument_name,
                               target=self.target,
                               local_dir=self.local_dir,
                               data_url=self.data_url)
        self.base_dir_template = str(self.dataset.data_dir)

    def add_arguments(self) -> None:
        """ Hook for adding more arguments in derived workflows """
        pass

    def override_configuration(self, **kwargs):
        """ Hook for overriding the configuration in derived workflows """
        pass

    def process(self):
        """ Load and override the configuration and then run the workflow """
        logger.info(f"Workflow {c.name(self.__class__.__name__)} is about to run the following steps: "
                    f"{', '.join([c.name(step) for step in self.steps])}")

        self.configuration = pyreduce.configuration.get_configuration_for_instrument(self.instrument_name, plot=1)
        self.override_configuration()

        return pyreduce.reduce.main(
            self.instrument_name,
            self.target,
            self.night,
            self.mode,
            steps=self.steps,
            base_dir_template=self.base_dir_template,
            input_dir_template=self.input_dir_template,
            output_dir_template=self.output_dir_template,
            configuration=self.configuration,
            order_range=self.order_range,
        )
