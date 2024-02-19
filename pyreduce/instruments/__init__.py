from .common import Instrument, InstrumentWithModes

from pyreduce.instruments.andes.andes import ANDES
from pyreduce.instruments.crires_plus.crires_plus import CRIRES_PLUS
from pyreduce.instruments.uves.uves import UVES

__all__ = ['ANDES', 'CRIRES_PLUS', 'UVES']
