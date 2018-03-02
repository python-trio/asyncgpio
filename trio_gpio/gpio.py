from . import libgpiod as gpio

import sys

class Chip:
	_chip = None
	def __init__(self, num):
		self.num = num
	
	def __enter__(self):
		self._chip = gpio.lib.gpiod_chip_open_by_number(self.num)
		if self._chip == gpio.ffi.NULL:
			raise OSError("unable to open chip")
		return self
	
	def __exit__(self, *tb):
		gpio.lib.gpiod_chip_close(self._chip)
		self._chip = None

	def line(self, offset):
		return Line(self, offset)

class Line:
	_line = None

	def __init__(self, chip, offset, consumer=sys.argv[0][:-3], direction=gpio.DIRECTION_INPUT, default=False, flags=0):
		self._chip = chip
		self._offset = offset
		self._direction = direction
		self._consumer = consumer.encode("utf-8")
		self._default = default
		self._flags = flags
	
	def __enter__(self):
		self._line = gpio.lib.gpiod_chip_get_line(self._chip._chip, self._offset)
		if self._line == gpio.ffi.NULL:
			raise OSError("unable to get line")
		if self._direction == gpio.DIRECTION_INPUT:
			r = gpio.lib.gpiod_line_request_input_flags(self._line, self._consumer, self._flags)
		elif self._direction == gpio.DIRECTION_OUTPUT:
			r = gpio.lib.gpiod_line_request_output_flags(self._line, self._consumer, self._flags, self._default)
		else:
			self.__exit__()
			raise RuntimeError("Unknown direction")
		if r != 0:
			self.__exit__()
			raise OSError("unable to set direction")
		return self

	def __exit__(self, *tb):
		gpio.lib.gpiod_line_release(self._line)
		self._line = None

	def _is_open(self):
		if self._line is None:
			raise RuntimeError("Line is not open")

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
		return gpio.lib.is_open_drain(self._line)

	@property
	def is_open_source(self):
		self._is_open()
		return gpio.lib.is_open_source(self._line)

	@property
	def is_used(self):
		self._is_open()
		return gpio.lib.is_used(self._line)

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
	
	def events(self, type=gpio.REQUEST_EVENT_RISING_EDGE, flags=0):
		"""
		Request events.

		Usage::
			
			async for event in self.events():
				print(event)
		"""
		self._is_open()
		if gpio.lib.line_event_request_type(self._line, self._consumer.encode("utf-8"), flags, type) != 0:
			raise OSError("unable to request events")
		return self

	def _update(self):
		self._is_open()
		if gpio.lib.gpiod_line_update(self._line) == -1:
			raise OSError("unable to update state")

	def __aiter__(self):
		self._is_open()
		if not self._requested:
			raise RuntimeError("You need to call .events()")
		return self
	
	async def __anext__(self):
		self._is_open()
		event = gpio.ffi.new("struct gpiod_line_event*")
		fd = gpio.lib.gpiod_line_event_get_fd(self._line)
		if fd < 0:
			raise OSError("line is closed")
		await trio.hazmat.wait_readable(fd)
		self._is_open()
		r = gpio.lib.gpiod_line_event_read_fd(fd, event)
		if r != 0:
			raise OSError("unable to read update")
		return event
	
	async def aclose(self):
		"""close the iterator."""
		pass

