"""
Provides example datasets for the examples

This requires the server to be up and running,
if data needs to be downloaded
"""
import abc
import logging
import tarfile
from pathlib import Path

import wget

logger = logging.getLogger(__name__)


class Dataset(metaclass=abc.ABCMeta):
    server_url: str = r"http://sme.astro.uu.se/pyreduce/"
    instrument_name: str = None
    _local_dir_template: str = None
    _data_dir: Path = None

    @property
    def local_dir_template(self) -> str:
        return self._local_dir_template

    @property
    def data_dir(self) -> Path:
        return self._data_dir

    @staticmethod
    def load_data_from_server(filename: str, directory: Path) -> None:
        wget.download(f"{Dataset.server_url}{filename}", out=str(directory / filename))

    def __init__(self, *, local_dir_template: str | None = None):
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
        local_dir_template : str, optional
            directory to save data at (default: "./")

        Returns
        -------
        dataset_dir : str
            directory where the data was saved
        """
        # If no local dir is provided, use the parent of current file
        self._local_dir_template = local_dir_template if local_dir_template is not None else Path(__file__).parent.name

        # Load data if necessary
        fname = f"{self.instrument_name}.tar.gz"
        self._data_dir = Path(self._local_dir_template) / "datasets" / self.instrument_name
        filename = self.data_dir / fname

        self._data_dir.mkdir(parents=True, exist_ok=True)
        if filename.is_file():
            logger.info(f"Using existing dataset {self.instrument_name} from {filename}")
        else:
            logger.info(f"Dataset {self.instrument_name} does not exist at {filename}, downloading to {self.data_dir}")
            self.load_data_from_server(fname, self.data_dir)

        # Extract the downloaded .tar.gz file
        with tarfile.open(filename) as file:
            raw_dir = self.data_dir / "raw"
            names = [f for f in file if not (raw_dir / f.name).is_file()]
            if len(names) != 0:
                logger.info(f"Extracting data from tarball {file.name}")
                file.extractall(path=raw_dir, members=names)

        #def download_and_extract(root_url: str = r"http://sme.astro.uu.se/pyreduce/"):



class DatasetUVES(Dataset):  # pragma: no cover
    instrument_name: str = "UVES"
    target: str = "HD132205"


class DatasetHARPS(Dataset):  # pragma: no cover
    instrument_name: str = "HARPS"
    target: str = "HD109200"


class DatasetLICK_APF(Dataset):  # pragma: no cover
    instrument_name: str = "LICK_APF"
    target: str = "KIC05005618"


class DatasetMCDONALD(Dataset):  # pragma: no cover
    instrument_name: str = "JWST_MIRI"
    target: str = "?"


class DatasetXSHOOTER(Dataset):  # pragma: no cover
    instrument_name: str = "XSHOOTER"
    target: str = "Ux-Ori"


class DatasetJWST_MIRI(Dataset):  # pragma: no cover
    instrument_name: str = "JWST_MIRI"
    target: str = "?"


class DatasetJWST_NIRISS(Dataset):  # pragma: no cover
    instrument_name: str = "JWST_NIRISS"
    target: str = "?"


class DatasetKECK_NIRSPEC(Dataset):  # pragma: no cover
    instrument_name: str = "KECK_NIRSPEC"
    target: str = "GJ1214"


class DatasetMETIS(Dataset):
    instrument_name: str = "METIS"
    target: str = None
