from .instrument import Instrument, InstrumentWithModes

from .andes.andes import ANDES
from .crires_plus.crires_plus import CRIRES_PLUS
from .uves.uves import UVES
from .metis_ifu.metis import METIS

__all__ = ['Instrument', 'InstrumentWithModes',
           'ANDES', 'CRIRES_PLUS', 'UVES', 'METIS',
           # TODO Add the rest too
           ]
