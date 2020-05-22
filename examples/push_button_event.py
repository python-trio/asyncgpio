import time
import anyio
import asyncgpio as gpio

"""
This example is taken out of my furnace controller.
It has been tested with Raspberry Pi Zero W and I assume it will work with any board supported by asyncgpio.
Use at your own risk.

If you aren't sure about how to hook up a button and led to your board, there are a lot of examples online.

Thank you @smurfix, who wrote asyncgpio and @njsmith and other in glitter:python-trio/general room
who helped me out.
"""


class Led:
	# This class turns on and off the power to a pin.
	# Two events are setup for turning off an on the pin. Both events need to be 
	# called at the same time or trio might await at the wrong spot.
	def __init__(self, line):
		self.x = line
		self._on = anyio.create_event()
		self._off = anyio.create_event()

	async def liteon(self):
		with gpio.open_chip() as chip:
			with chip.line(self.x).open(direction=gpio.DIRECTION_OUTPUT) as line:
				self._on.clear()
				await self._off.set()
				while True:
					if self._on.is_set():
						line.value = 1
						# print('lite on')
						await self._off.wait()
						self._on = anyio.create_event()
					elif self._off.is_set():
						line.value = 0
						# print('lite off')d
						await self._on.wait()
						self._off = anyio.create_event()
					else:
						# should never be reached.
						# if the code does reach here,
						# turn off the power to whatever is being powered
						print('error: both are off.')
						await self._off.set()


class Button:
	# Add the events tthe button is attached to and the on off event are passed into the class.
	# The class listens for the voltage to rise then reverses whatever the current settings are.
	def __init__(self, line, event_on, event_off):
		self.y = line
		self._on = event_on
		self._off = event_off

	async def push(self):
		with gpio.Chip(0) as c:
			in_ = c.line(self.y)
			with in_.monitor(gpio.REQUEST_EVENT_RISING_EDGE):
				last = 0
				async for e in in_:
					# This section is for debouncing the button.
					# As a button is pushed and released the voltage can rapidly go up and down many times
					# when the user only meant one push. To limit this, a delay is add to ignore changes.
					# This can be adjusted depending on the button and the respose.
					secs, ns_secs = e.timestamp
					now = float(str(secs)+'.'+str(ns_secs))
					if now >= last + .25:
						print('button', e.value, secs, ns_secs, now)
						if self._on.is_set():
							await self._off.set()
						else:
							await self._on.set()
					last = now

# Asyncgpio uses the BCM pin numbering. So, the led is on the pin 21 
# and the button that controls the yellow is hooked to pin 23.
yellow = Led(21) 
yellowbutton = Button(23, yellow._on, yellow._off)


async def main(y):
	async with anyio.create_task_group() as nursery:
		await nursery.spawn(yellowbutton.push)
		await nursery.spawn(yellow.liteon)


if __name__ == "__main__":
    anyio.run(main, 1, backend="trio")
