"""Top-level package for trio-gpio."""

from ._version import __version__

from .gpio import Chip
from .libgpiod import *

