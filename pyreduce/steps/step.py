import abc
import datetime

from pathlib import Path

from pyreduce.instruments import Instrument


class Step(metaclass=abc.ABCMeta):
    """ Abstract parent class for all steps. """

    def __init__(self,
                 instrument: str,
                 mode: str,
                 target: str,
                 night,
                 output_dir_template: str,
                 order_range,
                 **config):
        self._depends_on: list[str] = []
        self._load_depends_on: list[str] = []

        # Name of the instrument
        self.instrument: Instrument = instrument  # TODO Switch to Instrument or load?
        # Name of the instrument mode
        self.mode: str = mode
        # Name of the observation target
        self.target: str = target
        # Date of the observation (as a string)
        self.night: datetime.date = night
        # First and Last(+1) order to process
        self.order_range: tuple[int, int] = order_range
        # Whether to plot the results or the progress of this step
        self.plot: bool = config.get("plot", False)
        # Title used in the plots, if any
        self.plot_title: str | None = config.get("plot_title", None)
        self._output_dir_template: str = output_dir_template

    @abc.abstractmethod
    def run(self, files, *args):  # pragma: no cover
        """Execute the current step

        This should fail if files are missing or anything else goes wrong.
        If the user does not want to run this step, they should not specify it in steps.

        Parameters
        ----------
        files : list(str)
            data files required for this step
        """
        raise NotImplementedError

    def save(self, *args):  # pragma: no cover
        """Save the results of this step

        Parameters
        ----------
        *args : obj
            things to save
        """
        raise NotImplementedError

    def load(self, **kwargs):  # pragma: no cover
        """Load results from a previous execution

        If this raises a FileNotFoundError, run() will be used instead
        For calibration steps it is preferred however to print a warning
        and return None. Other modules can then use a default value instead.

        Raises
        ------
        NotImplementedError
            Needs to be implemented for each step
        """
        raise NotImplementedError

    @property
    def depends_on(self):
        """list(str): Steps that are required before running this step"""
        return list(set(self._depends_on))

    @property
    def load_depends_on(self) -> list[str]:
        """ list(str): Steps that are required before loading data from this step"""
        return list(set(self._load_depends_on))

    @property
    def output_dir(self) -> Path:
        """ Fill the output dir template and return a Path where outputs will be stored """
        return Path(
            self._output_dir_template.format(
                instrument=self.instrument.name.upper(),
                target=self.target,
                night=self.night.isoformat(),
                mode=self.mode,
            )
        )

    @property
    def prefix(self) -> str:
        """ Temporary file prefix """
        name = self.instrument.name.lower()
        if self.mode is not None and self.mode != "":
            mode = self.mode.lower()
            return f"{name}_{mode}"
        else:
            return name
