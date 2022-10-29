.. trio_asyncgpio_demo documentation master file, created by
   sphinx-quickstart on Mon Jan  4 16:25:45 2021.

trio_asyncgpio_demo overview
============================

The file trio_asyncgpio_demo.py contains three examples of how a the state of a GPIO pin can be tracked:

1. Within a loop
2. With a function
3. By a class instance that changes the state of another pin either mirroring or inverting it

The code has quite a few debug print statements to help track how different portions work together and to
facilitate debugging. Loguru is used as a logger. This may be installed using:
::
        pip install loguru

The logging level for loguru is set via an environment variable. For example, to change to the logging
level of info from the default of debug:
::
         export LOGURU_LEVEL=INFO

To resume full logging, set the above environment variable to DEBUG.

PinWatcher
==========

This is the class that coordinates everything. It monitors the state of a pin and manages startup and shutdown. 

There are two categories of events that that are managed by PinWatcher:

1. An initialized event. This is set once PinWatcher has been initialized. Functions and class instances can await this event.
2. A list of events that have been added by functions or class instances. This is set at initialization and when the pin changes state.

**Event list**

Functions and class instances register pin change event notification requests by placing a Trio event on the event list. 
This is done, as can be seen in the examples, by adding the following statement:
::
   pin_watcher.on_notify = event_to_watch = trio.Event()

Upon state change of a pin, the internal method _pin_monitor will execute either _notify_on_waiting or 
_notify_off_waiting depending on the true or false state of the pin. These methods are similar. They 
traverse the list of events, setting each, and then creating a new empty list. Functions and methods await 
the event that they have set (event_to_watch) via the statement:
::
   await event_to_watch.wait()

With the exception of the polling loop, this pattern is used for all examples.

**Maximum length of event list**

The maximum length of the list of events is set by the variable _max_notify_list_length

In the sample, this is set to 15. A runtime error will be generated if that limit is exceeded.
This is useful for debugging and testing since most of the code is in infinite loops and 
it is easy to generate excessive numbers of events.

**Coordinated shutdown**

This demo contains code that may be run as a daemon. 
PinWatcher will coordinate shutdown for clients (functions, polling loops and class instances). 
This is accomplished by two loops: an outer one that listens for signals, 
and an inner one where clients are run that should be shutdown based on the receipt of a signal.

The code is based on the following:

    https://github.com/python-trio/trio/issues/569

    https://github.com/python-trio/trio/blob/master/notes-to-self/graceful-shutdown-idea.py

The method _listen_for_shutdown_signals is placed in the outer loop, which in this example is named daemon. 
Everything else is run in the inner loop, which in the example is named nursery.

Clients enclose continuously running code in the statement:
::
   with pin_watcher.cancel_on_shutdown():

All examples use this pattern, along with the variable pin_watcher.shutting_down, to manage graceful shutdown. 
This example takes a very simplistic approach to handling signals. In some cases it may be beneficial to 
handle signals a specific way or to provide a timeout.

**PinWatcher Documentation**

.. autoclass:: trio_asyncgpio_demo.PinWatcher
   :members:

PinFollower
===========

This class provides the ability for a pin to follow the state of the one being monitored, either 
mirroring or inverting the state of the monitored pin.

**PinFollower Documentation**

.. autoclass:: trio_asyncgpio_demo.PinFollower
   :members:

monitor_pin_loop(pin_watcher)
=============================

An example of monitoring the state of a pin in a loop.

In this example the loop is monitoring the state of the pin monitored by pin_watcher.
Since the example is just a loop that sleeps between checking on the state, fast transitions will be missed.

func_on_trigger(pin_watcher)
============================

An example of a function that is is waiting on the state of a pin to be true. This is executed each time the 
pin changes from false to true and if the initial state of the monitored pin is true.

func_off_trigger(pin_watcher)
=============================

An example of a function that is is waiting on the state of a pin to be false. This is executed each time the 
pin changes from true to false and if the initial state of the monitored pin is false.

Performance on a Raspberry Pi 3B
================================

To get a feeling for the performance of this demo code, an input pin (in_pin) was toggled with a 100 Hz square wave. 
Two pins were configured to follow in_pin. The first (pin_mirror) mirrored the input, while the second (pin_invert) 
inverted the signal. The result of collecting delay information for around 100 true to false transitions is 
shown in the table below. Logging was set to INFO for the performance test.

.. list-table:: Delay in milliseconds from in_pin with one pin following input and another inverting it:
   :widths: 30 15 15 15
   :header-rows: 1

   *  - Pin
      - Avg (ms)
      - Min (ms)
      - Max (ms)
   *  - pin_invert
      - 1.04
      - 0.87
      - 1.38
   *  - pin_mirror
      - 1.04
      - 0.87
      - 1.75

For a few rounds of testing at 100 Hz, nothing concerning showed up on the logic analyzer. At 200 Hz, there 
were cases where pin_invert and pin_mirror outputs lagged sufficiently that some of the transitions were 
shorter than expected while others were longer. With input at 100 Hz and the logging level set to INFO, 
it was possible to run the test above as well as the functions that fire when logic levels change. Those 
functions don't really do anything, so this was more of a functional test than something that could 
be considered realistic.