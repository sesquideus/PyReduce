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
    server_url: str = r"http://sme.astro.uu.se/pyreduce/"
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

    @staticmethod
    def load_data_from_server(filename: str, directory: Path) -> None:
        wget.download(f"{Dataset.server_url}{filename}", out=str(directory / filename))

    def __init__(self,
                 instrument_name: str = None,
                 target: str = None,
                 *,
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
            self.load_data_from_server(fname, self.data_dir)

        # Extract the downloaded .tar.gz file
        with tarfile.open(filename) as file:
            raw_dir = self.data_dir / "raw"
            names = [f for f in file if not (raw_dir / f.name).is_file()]
            if len(names) != 0:
                logger.info(f"Extracting data from tarball {c.path(file.name)}")
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
