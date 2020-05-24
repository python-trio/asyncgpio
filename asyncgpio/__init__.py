"""Top-level package for asyncgpio."""

import sys

from .gpio import Chip
from .libgpiod import *  # noqa


def open_chip(num=None, label=None, consumer=sys.argv[0]):
    """Returns an object representing a GPIO chip.

    Arguments:
        num: Chip number. Defaults to zero.

        consumer: A string for display by kernel utilities.
            Defaults to the program's name.

    Returns:
        a :class:`asyncgpio.gpio.Chip` instance.
    """
    return Chip(num=num, label=label, consumer=consumer)
