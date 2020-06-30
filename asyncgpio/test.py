"""
This module contains helpers for testing async gpio, via the Linux kernel's
``gpio_mockup`` module (writing) and ``/sys/kernel/debug/cpio`` (monitoring).
"""

import os
import re
import anyio
import logging
import errno

from contextlib import asynccontextmanager
from collections import namedtuple

logger = logging.getLogger(__name__)

_r_chip = re.compile(
    "^(?P<chip>[a-z0-9]+): GPIOs (?P<base>[0-9]+)-(?:.*, (?P<name>[-_a-zA-Z0-9]+): *$)?"
)
_r_pin = re.compile("^gpio-(?P<pin>[0-9]+) \\(.*\\) (?P<dir>in|out) +(?P<val>hi|lo)")

Pin = namedtuple("Pin", ["out", "level"])


class _GpioPin:
    """
    Code representing one GPIO pin.
    """

    fd = None

    def __init__(self, watcher: "GpioWatcher", chip: str, pin: int):
        self.watcher = watcher
        self.chip = chip
        self.pin = pin
        self.mon = set()
        self.state = (None, None)
        try:
            self.fd = os.open(
                os.path.join(watcher.debugfs_path, "gpio-mockup-event", chip, str(pin)),
                os.O_WRONLY,
            )
        except EnvironmentError as exc:
            if exc.errno != errno.ENOENT:
                raise

    def __del__(self):
        if self.fd is not None:
            os.close(self.fd)
            del self.fd

    @asynccontextmanager
    async def watch(self):
        """
        An async context manager that returns an iterator for changes of
        this pin.

        Values are (out,level) tuples of bool, with "out" and "high"
        represented as True.
        """
        q = anyio.create_queue(10)
        self.mon.add(q)
        try:
            yield q
        finally:
            self.mon.remove(q)

    async def see(self, write: bool, level: bool):
        s = (write, level)
        if self.state == s:
            return
        self.state = s
        logger.debug("SEE %s %d %s", self.chip, self.pin, self.state)
        for cb in list(self.mon):
            await cb.put(s)

    def set(self, value: bool):
        logger.debug("SET %s %d %s", self.chip, self.pin, value)
        if self.fd is None:
            raise RuntimeError(
                "Pin %s/%d is not controlled via the 'gpio_mockup' module" % (self.chip, self.pin)
            )
        os.write(self.fd, b"1" if value else b"0")
        # os.lseek(self.fd, 0, os.SEEK_SET)


class GpioWatcher:
    """
    Code which triggers callbacks whenever a GPIO pin changes.

    This class polls `/sys/kernel/debug/gpio` (can be overridden).
    """

    tg = None  # for .run

    def __init__(
        self,
        interval: float = 0.2,
        debugfs_path: str = "/sys/kernel/debug",
        sysfs_path: str = "/sys",
    ):
        self.interval = interval
        self.gpio = open(os.path.join(debugfs_path, "gpio"), "r")
        self.targets = dict()  # chip > line > _GpioPin
        #       self.names = {}
        self.sysfs_path = sysfs_path
        self.debugfs_path = debugfs_path
        # gpio_dir = os.path.join(sysfs_path, "class", "gpio")

    #       for d in os.listdir(gpio_dir):
    #           try:
    #               with open(os.path.join(gpio_dir,d,"label"),"r") as f:
    #                   n = f.read().strip()
    #           except EnvironmentError as e:
    #               if e.errno == errno.ENOTDIR:
    #                   continue
    #               raise
    #           else:
    #               self.names[d] = n

    def monitor(self, chip: str, pin: int):
        """
        Shortcut for 'self.pin(chip, pin).watch()'.
        """
        return self.pin(chip, pin).watch()

    def pin(self, chip: str, pin: int, create: bool = True):
        """
        Returns a pins corresponding GpioPin
        """
        #       chip = self.names[chip]
        try:
            c = self.targets[chip]
        except KeyError:
            if not create:
                raise
            self.targets[chip] = c = dict()
        try:
            p = c[pin]
        except KeyError:
            if not create:
                raise
            c[pin] = p = _GpioPin(self, chip, pin)
        return p

    async def _watch(self):
        # The actual monitor.
        while True:
            await self.check_pins()
            await anyio.sleep(self.interval)

    async def check_pins(self):
        """
        Read the GPIO debug file and update pin states
        """
        chip = None
        base = None

        for line in self.gpio:
            line = line.strip()
            if not line:
                chip = None
                continue
            if chip is None:
                r = _r_chip.match(line)
                if not r:
                    raise ValueError(line)
                chip = r.group("name")
                if not chip:
                    chip = r.group("chip")
                base = int(r.group("base"))
            else:
                r = _r_pin.match(line)
                if not r:
                    breakpoint()
                    raise ValueError(line)
                pin = int(r.group("pin")) - base
                out = r.group("dir") == "out"
                val = r.group("val") == "hi"

                try:
                    pin = self.pin(chip, pin, create=False)
                except KeyError:
                    pass
                else:
                    await pin.see(out, val)
        self.gpio.seek(0)

    @asynccontextmanager
    async def run(self):
        """
        This async context manager controls the monitoring loop.
        """
        async with anyio.create_task_group() as tg:
            self.tg = tg
            await tg.spawn(self._watch)
            try:
                yield self
            finally:
                self.tg = None
                await tg.cancel_scope.cancel()
