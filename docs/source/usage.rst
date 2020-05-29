
Using AsyncGPIO
===============

.. module: asyncgpio

Using AsyncGPIO generally consists of three steps:
Accessing the chip, referring to a GPIO line within that chip.
and actually using the line for input, output, or monitoring.

AsyncGPIO currently only works with anyio's Trio backend.

Accessing a GPIO chip
---------------------

GPIO chips are accessed by their number. You usually find them as ``/dev/gpiochipN``
where N starts at zero.

AsyncGPIO refers to GPIO chips by their sequence number.
You need to refer to your hardware's documentation to discover which chip to use,
assuming there's more than one.

::
    import asyncgpio as gpio

    def main():
        with gpio.open_chip(0, consumer="example") as chip:
            do_something_with(chip)

The ``consumer`` argument is optional. It describes your code to the kernel, so that
a program which enumerates GPIO users can display who currently uses the pin in question.

.. autofunction:: asyncgpio.open_chip

Referring to a line
-------------------

Via the chip object, you can refer to single GPIO lines. 

You need to refer to your hardware's documentation to discover which line to use.

.. note::

    Accessing a line in a way not intended by hardware (i.e. driving a line
    as an output that's actually an input) may damage your computer or its
    periphera(s).

.. automethod: asyncgpio.gpio.Chip.line

.. note::

   ``libgpiod`` has functions for bulk referrals which allow you to access multiple lines
   at the same time. Yo may wonder why these are missing from AsyncGPIO. The answer is that
   the kernel's GPIO interface does not have functions that affect multiple lines; if you
   need them for convenience it's easer to write appropriate Python methods, than to do the
   packing+unpacking of values into C-language structures that these bulk methods require.


Using a line
------------

A :class:`asyncgpio.gpio.Line` object just describes a GPIO line; before you can actually
use it, you need to request it from the kernel (which also prevents anybody else from using
the line).

.. note:: Before doing *that*, you might need to de-allocate the line from any
   kernel driver that uses it for its own purpose. You typically do that via sysfs.

   This includes the deprecated ``sysfs`` GPIO driver! That is, if you previously marked
   a GPIO line for your use by running ``echo 12 >/sys/class/gpio/export`` or similar,
   you need to do ``echo 12 >/sys/class/gpio/unexport`` before your program can access
   line 12.

.. automethod: asyncgpio.Line.open

Output
~~~~~~

Conceptually, controlling on a GPIO line is simple::

    with chip.line(20).open(direction=gpio.DIRECTION_OUTPUT) as line:
        line.value = 1

However, the code above will not work because as soon as the ``with`` block is exited,
the line is closed. Most likely, this means that the line will revert to its hardware
default.

Thus, if you want your light to be on for more than a few microseconds, the following
code might be a better idea::

    with chip.line(20).open(direction=gpio.DIRECTION_OUTPUT) as line:
        line.value = 1
        try:
            await anyio.sleep(5*60)
        finally:
            line.value = 0


Input
~~~~~

Reading a line is easy::

    with chip.line(20).open(direction=gpio.DIRECTION_INPUT) as line:
        if line.value:
            print("It's on!")

Like the previous example, this will immediately close the line, so if you need to access
a value more often (or if you want to make sure that no other program, or a misguided user,
can steal it) it's more efficient to use a long-running ``with`` block.

Monitoring
~~~~~~~~~~

If you want to watch when an input changes, periodically reading its value is not a good idea.
Polling eats CPU time (thus heating up your computer for no good reason), your
timing will be inaccurate, and your code will be scheduled with low priority because
it is continually busy.

Therefore, it's better to let the kernel signal changes to a GPIO device::

    with gpio.Chip(0) as c:
        with c.line(19).open(direction=gpio.DIRECTION_OUTPUT) as out_:
            wire = c.line(20)
            with wire.monitor(gpio.REQUEST_EVENT_BOTH_EDGES):
                async for e in in_:
                    print(e, "on" if e.value else "off", "at", e.time.strftime("%H:%M:%S"))

:: automethod: asyncgpio.gpio.Line.monitor

:: autoclass: asyncgpio.gpio.Event
   :members:

.. note::

   The kernel will send an initial message with the line's current state, thus even when you
   request e.g. only notifications for rising edges, the initial event may have a zero value.

