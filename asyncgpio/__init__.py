"""Top-level package for trio-gpio."""

import sys

from ._version import __version__  # noqa

from .gpio import Chip
from .libgpiod import *  # noqa


def open_chip(num=0, consumer=sys.argv[0]):
    """Returns an object representing a GPIO chip.

    Arguments:
        num: Chip number. Defaults to zero.

        consumer: A string for display by kernel utilities.
            Defaults to the program's name.

    Returns:
        a :class:`trio_gpio.gpio.Chip` instance.
    """
    return Chip(num, consumer=consumer)
