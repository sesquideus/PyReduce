from .instrument import Instrument, InstrumentWithModes

from .andes.andes import ANDES
from .crires_plus.crires_plus import CRIRES_PLUS
from .uves.uves import UVES
from .metis_ifu.metis_ifu import METIS_IFU
from .metis_lss.metis_lss import METIS_LSS

__all__ = ['Instrument', 'InstrumentWithModes',
           'ANDES', 'CRIRES_PLUS', 'UVES', 'METIS_LSS', 'METIS_IFU',
           # TODO Add the rest too
           ]
