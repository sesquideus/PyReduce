"""
Provides example datasets for the examples

This requires the server to be up and running,
if data needs to be downloaded
"""
import abc
import logging
import tarfile
import wget

from pathlib import Path

from pyreduce import colour as c

logger = logging.getLogger(__name__)


class Dataset(metaclass=abc.ABCMeta):
    # Static URL for download of prepared datasets
    server_url: str = r"http://sme.astro.uu.se/pyreduce/"
    # If None, use default server / name, otherwise download from here
    data_url: str = None
    instrument_name: str = None
    target: str = None
    _local_dir: Path = None
    _data_dir: Path = None

    @property
    def local_dir(self) -> Path:
        return self._local_dir

    @property
    def data_dir(self) -> Path:
        return self._data_dir

    def load_data_from_server(self) -> None:
        wget.download(f"{Dataset.server_url}{self.instrument_name}.tar.gz",
                      out=f"{self.data_dir}/{self.instrument_name}.tar.gz")

    def load_data_from_dropbox(self) -> None:
        wget.download(self.data_url, out=f"{self.data_dir}/{self.instrument_name}.tar.gz")

    def __init__(self,
                 instrument_name: str = None,
                 target: str = None,
                 *,
                 url: str = None,
                 local_dir: Path | None = None):
        """
        Load a dataset

        Note
        ----
        This method will not override existing files with the same
        name, even if they have a different content. Therefore,
        if the files were changed for any reason, the user has to
        manually delete them from the disk before using this method.

        Parameters
        ----------
        local_dir : str, optional
            directory to save data at (default: "./")
        """
        # If no local dir is provided, use the parent of current file
        self.instrument_name = instrument_name
        self.target = target

        if url is not None:
            self.server_url = url

        if local_dir is None:
            self._local_dir = Path(__file__).parent
        else:
            self._local_dir = local_dir

        logger.debug(f"Created a dataset for instrument {c.name(self.instrument_name)} "
                     f"and target {c.name(self.target)} at {c.path(str(self.local_dir))}")

        # Load data if necessary
        fname = f"{self.instrument_name}.tar.gz"
        self._data_dir = Path(self._local_dir) / "datasets" / self.instrument_name
        filename = self.data_dir / fname

        self._data_dir.mkdir(parents=True, exist_ok=True)
        if filename.is_file():
            logger.info(f"Using existing dataset {self.instrument_name} from {c.path(filename)}")
        else:
            logger.info(f"Dataset {c.name(self.instrument_name)} does not exist at {c.path(filename)}, "
                        f"downloading to {c.path(self.data_dir)}")
            if self.data_url is None:
                logger.debug(f"No data_url defined, defaulting to {c.path(self.server_url)}")
                self.load_data_from_server()
            else:
                logger.debug(f"Attempting to download from {c.path(self.data_url)}")
                self.load_data_from_dropbox()

        # Extract the downloaded .tar.gz file
        with tarfile.open(filename) as file:
            raw_dir = self.data_dir / "raw"
            names = [f for f in file if not (raw_dir / f.name).is_file()]
            if len(names) != 0:
                logger.info(f"Extracting data from tarball {c.path(file.name)}")
                file.extractall(path=raw_dir, members=names)
