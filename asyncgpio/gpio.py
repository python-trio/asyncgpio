from . import libgpiod as gpio

import sys
import anyio
import datetime


class Chip:
    """Represents a GPIO chip.

    Arguments:
        label: Chip label. Run "gpiodetect" to list GPIO chip labels.

        num: Chip number. Deprecated. Defaults to zero.
            Only used if you don't use a label.

        consumer: A string for display by kernel utilities.
            Defaults to the program name.

    """

    _chip = None

    def __init__(self, num=None, label=None, consumer=sys.argv[0]):
        self._num = num
        self._label = label
        if (num is None) == (label is None):
            raise ValueError("Specify either label or num")
        self._consumer = consumer

    def __repr__(self):
        if self._label is None:
            return "%s(%d)" % (self.__class__.__name__, self._num)
        else:
            return "%s(%s)" % (self.__class__.__name__, self._label)

    def __enter__(self):
        if self._label is None:
            self._chip = gpio.lib.gpiod_chip_open_by_number(self._num)
        else:
            self._chip = gpio.lib.gpiod_chip_open_by_label(self._label.encode("utf-8"))
        if self._chip == gpio.ffi.NULL:
            raise OSError("unable to open chip")
        return self

    def __exit__(self, *tb):
        gpio.lib.gpiod_chip_close(self._chip)
        self._chip = None

    def line(self, offset, consumer=None):
        """Get a descriptor for a single GPIO line.

        Arguments:
            offset: GPIO number within this chip. No default.
            consumer: override the chip's consumer, if required.
        """
        if consumer is None:
            consumer = self._consumer
        return Line(self, offset, consumer=consumer)


_FREE = 0
_PRE_IO = 1
_IN_IO = 2
_PRE_EV = 3
_IN_EV = 4
_IN_USE = {_IN_IO, _IN_EV}


class Line:
    """Represents a single GPIO line.

    Create this object by calling :meth:`Chip.line`.
    """

    _line = None
    _direction = None
    _default = None
    _flags = None
    _ev_flags = None
    _state = _FREE

    _type = None

    def __init__(self, chip, offset, consumer=sys.argv[0][:-3]):
        self._chip = chip
        self._offset = offset
        self._consumer = consumer.encode("utf-8")
        self.__consumer = gpio.ffi.new("char[]", self._consumer)

    def __repr__(self):
        return "<%s %s:%d %s=%d>" % (
            self.__class__.__name__,
            self._chip,
            self._offset,
            self._line,
            self._state,
        )

    def open(self, direction=gpio.DIRECTION_INPUT, default=False, flags=0):
        """
        Create a context manager for controlling this line's input or output.

        Arguments:
            direction: input or output. Default: gpio.DIRECTION_INPUT.
            flags: to request pull-up/down resistors or open-collector outputs.

        Example::
            with gpio.Chip(0) as chip:
                line = chip.line(16)
                with line.open(direction=gpio.DIRECTION_INPUT) as wire:
                    print(wire.value)
        """
        if self._state in _IN_USE:
            raise OSError("This line is already in use")
        self._direction = direction
        self._default = default
        self._flags = flags
        self._state = _PRE_IO
        return self

    def __enter__(self):
        """Context management for use with :meth:`open` and :meth:`monitor`."""
        if self._state in _IN_USE:
            raise OSError("This line is already in use")
        if self._state == _FREE:
            raise RuntimeError("You need to call .open() or .event()")
        self._line = gpio.lib.gpiod_chip_get_line(self._chip._chip, self._offset)
        if self._line == gpio.ffi.NULL:
            raise OSError("unable to get line")

        if self._state == _PRE_IO:
            self._enter_io()
        elif self._state == _PRE_EV:
            self._enter_ev()
        else:
            raise RuntimeError("wrong state", self)
        return self

    def _enter_io(self):
        if self._direction == gpio.DIRECTION_INPUT:
            r = gpio.lib.gpiod_line_request_input_flags(self._line, self._consumer, self._flags)
        elif self._direction == gpio.DIRECTION_OUTPUT:
            r = gpio.lib.gpiod_line_request_output_flags(
                self._line, self._consumer, self._flags, self._default
            )
        else:
            self.__exit__()
            raise RuntimeError("Unknown direction")
        if r != 0:
            self.__exit__()
            raise OSError("unable to set direction")
        self._state = _IN_IO
        return self

    def _enter_ev(self):
        req = gpio.ffi.new("struct gpiod_line_request_config*")
        req.consumer = self.__consumer
        req.request_type = self._type
        req.flags = self._flags
        if gpio.lib.gpiod_line_request(self._line, req, 0) != 0:
            raise OSError("unable to request event monitoring")
        self._state = _IN_EV

    def __exit__(self, *tb):
        if self._line is not None:
            try:
                gpio.lib.gpiod_line_release(self._line)
            finally:
                self._line = None
        self._state = _FREE

    def _is_open(self):
        if self._state not in _IN_USE:
            raise RuntimeError("Line is not open", self)

    @property
    def value(self):
        self._is_open()
        return gpio.lib.gpiod_line_get_value(self._line)

    @value.setter
    def value(self, value):
        self._is_open()
        gpio.lib.gpiod_line_set_value(self._line, value)

    @property
    def direction(self):
        if self._line is None:
            return self._direction
        return gpio.lib.gpiod_line_direction(self._line)

    @property
    def active_state(self):
        self._is_open()
        return gpio.lib.gpiod_line_active_state(self._line)

    @property
    def is_open_drain(self):
        self._is_open()
        return gpio.lib.gpiod_line_is_open_drain(self._line)

    @property
    def is_open_source(self):
        self._is_open()
        return gpio.lib.gpiod_line_is_open_source(self._line)

    @property
    def is_used(self):
        self._is_open()
        return gpio.lib.gpiod_line_is_used(self._line)

    @property
    def offset(self):
        if self._line is None:
            return self._offset
        return gpio.lib.gpiod_line_offset(self._line)

    @property
    def name(self):
        self._is_open()
        n = gpio.lib.gpiod_line_name(self._line)
        if n == gpio.ffi.NULL:
            return None
        return n

    @property
    def consumer(self):
        if self._line is None:
            return self._consumer
        n = gpio.lib.gpiod_line_consumer(self._line)
        if n == gpio.ffi.NULL:
            return None
        return gpio.ffi.string(n).decode("utf-8")

    def monitor(
        self, type=gpio.REQUEST_EVENT_RISING_EDGE, flags=0
    ):  # pylint: disable=redefined-builtin
        """
        Monitor events.

        Arguments:
            type: which edge to monitor
            flags: REQUEST_FLAG_* values (ORed)

        Usage::

            with gpio.Chip(0) as chip:
                line = chip.line(13)
                with line.monitor():
                    async for event in line:
                        print(event)
        """
        if self._state in _IN_USE:
            raise OSError("This line is already in use")
        self._state = _PRE_EV
        self._type = type
        self._flags = flags
        return self

    def _update(self):
        self._is_open()
        if gpio.lib.gpiod_line_update(self._line) == -1:
            raise OSError("unable to update state")

    def __iter__(self):
        raise RuntimeError("You need to use 'async for', not 'for'")

    async def __aenter__(self):
        raise RuntimeError("You need to use 'with', not 'async with'")

    async def __aexit__(self, *_):
        raise RuntimeError("You need to use 'with', not 'async with'")

    def __aiter__(self):
        if self._state != _IN_EV:
            raise RuntimeError("You need to call 'with LINE.monitor() / async for event in LINE'")
        return self

    async def __anext__(self):
        if self._state != _IN_EV:
            raise RuntimeError("wrong state")

        ev = gpio.ffi.new("struct gpiod_line_event*")
        fd = gpio.lib.gpiod_line_event_get_fd(self._line)
        if fd < 0:
            raise OSError("line is closed")
        await anyio.wait_socket_readable(fd)
        self._is_open()
        r = gpio.lib.gpiod_line_event_read_fd(fd, ev)
        if r != 0:
            raise OSError("unable to read update")
        return Event(ev)

    async def aclose(self):
        """close the iterator."""
        pass


class Event:
    """Store a Pythonic representation of an event
    """

    def __init__(self, ev):
        if ev.event_type == gpio.EVENT_RISING_EDGE:
            self.value = 1
        elif ev.event_type == gpio.EVENT_FALLING_EDGE:
            self.value = 0
        else:
            raise RuntimeError("Unknown event type")
        self._ts_sec = ev.ts.tv_sec
        self._ts_nsec = ev.ts.tv_nsec

    @property
    def timestamp(self):
        """Return a (second,nanosecond) tuple for fast timestamping"""
        return (self._ts_sec, self._ts_nsec)

    @property
    def time(self):
        """Return the event's proper datetime"""
        return datetime.datetime.fromtimestamp(self._ts_sec + self._ts_nsec / 1000000000)

    def __repr__(self):
        return "<%s @%s>" % (self.value, self.time)
