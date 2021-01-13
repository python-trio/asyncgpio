import trio
from contextlib import asynccontextmanager
import asyncgpio as gpio
from loguru import logger
import signal
import sys


class PinWatcher:
    """Watch a pin and maintain a list of events to be triggered based on the pin's state.
    Manage initialization and shutdown for objects reacting to pin state changes.

    Arguments::

        chip_id: the name of the chip. The command gpiodetect is helpful for identifying the chip_id.

        pin: the input pin number that is being monitored.

        on_notify: an event that will be set when the pin is true.

        off_notify: an event that will be set when the pin is false.
    """

    def __init__(self, chip_id, pin, on_notify=None, off_notify=None):
        self._chip_id = chip_id
        self._pin = pin
        self._initialized = trio.Event()
        self._on_notify_list = on_notify
        if self._on_notify_list is None:
            self._on_notify_list = []
        self._off_notify_list = off_notify
        if self._off_notify_list is None:
            self._off_notify_list = []
        # limit the number of events that will be notified for on or off condition
        self._max_notify_list_length = 15
        # shutdown code is from https://github.com/python-trio/trio/blob/master/notes-to-self/graceful-shutdown-idea.py
        self._shutting_down = False
        self._cancel_scopes = set()

    @property
    def initialized(self):
        return self._initialized

    @property
    def state(self):
        return self._current_state

    @property
    def on_notify(self):
        return self._on_notify_list

    @on_notify.setter
    def on_notify(self, new_on_event):
        if len(self._on_notify_list) <= self._max_notify_list_length:
            self._on_notify_list.append(new_on_event)
        else:
            raise RuntimeError(
                f'Adding to on_notify_list failed, exceeds maximum number of entries which is currently {self._max_notify_list_length}')

    @property
    def off_notify(self):
        return self._off_notify_list

    @off_notify.setter
    def off_notify(self, new_off_event):
        if len(self._off_notify_list) <= self._max_notify_list_length:
            self._off_notify_list.append(new_off_event)
        else:
            raise RuntimeError(
                f'Adding to off_notify_list failed, exceeds maximum number of entries which is currently {self._max_notify_list_length}')

    @property
    def shutting_down(self):
        return self._shutting_down

    def _notify_on_waiting(self):
        """Traverse the list of events that should be notified that the pin is on, setting each.
        """
        if self._on_notify_list:
            for notify_item in self._on_notify_list:
                notify_item.set()
        self._on_notify_list = []

    def _notify_off_waiting(self):
        """Traverse the list of events that should be notified that the pin is off, setting each.
        """
        if self._off_notify_list:
            for notify_item in self._off_notify_list:
                notify_item.set()
        self._off_notify_list = []

    def _start_shutdown(self):
        """Begin the shutdown process.
        """
        logger.info(f'starting shutdown')
        self._shutting_down = True
        self._notify_on_waiting()
        self._notify_off_waiting()
        for cancel_scope in self._cancel_scopes:
            cancel_scope.cancel()

    def cancel_on_shutdown(self):
        """Cancel scopes upon shutdown

        Usage::

            with self.cancel_on_shutdown():
                some code that should run until shutdown, likely an infinite loop
        """
        cancel_scope = trio.CancelScope()
        self._cancel_scopes.add(cancel_scope)
        if self._shutting_down:
            cancel_scope.cancel()
        return cancel_scope

    async def _pin_monitor(self):
        """Monitor a pin and notify any functions and/or class instances that are waiting for events to be set when state changes.
        """
        with self.cancel_on_shutdown():
            # Trio checkpoint to facilitate checking on shutdown signals
            await trio.sleep(0)
            with gpio.Chip(label=self._chip_id) as chip:
                pin_in = chip.line(self._pin)
                with pin_in.open(direction=gpio.DIRECTION_INPUT) as current_pin:
                    self._current_state = True if current_pin.value else False
                    logger.debug(
                        f'---- pin {self._pin} initial state is {self._current_state} ----')
                    # Notify dependent class instances and functions that monitoring has started
                    self.initialized.set()
                    logger.info(f'_pin_monitor has started')
                    # Trio checkpoint so that waiting lists are ready
                    await trio.sleep(0)
                    if self._current_state:
                        self._notify_on_waiting()
                    else:
                        self._notify_off_waiting()
                with pin_in.monitor(gpio.REQUEST_EVENT_BOTH_EDGES):
                    async for pin_event in pin_in:
                        if pin_event.value:
                            logger.debug(f'---- pin {self._pin} is true ----')
                            self._current_state = True
                            self._notify_on_waiting()
                        else:
                            logger.debug(f'---- pin {self._pin} is false ----')
                            self._current_state = False
                            self._notify_off_waiting()
        logger.info(f'pin_monitor has shutdown')
        if self.shutting_down:
            return

    async def _listen_for_shutdown_signals(self):
        """Listen for signals, potentially uniquely handling different signals, and initiating shutdown of event loops.
        """
        logger.debug(f'listening for shutdown signals')
        with trio.open_signal_receiver(signal.SIGINT, signal.SIGTERM, signal.SIGHUP) as signals:
            async for signal_number in signals:
                logger.debug(f'---- a shutdown signal has been received ----')
                if signal_number == signal.SIGINT:
                    logger.debug(f'received SIGINT, running start_shutdown')
                elif signal_number == signal.SIGTERM:
                    logger.debug(f'received SIGTERM, running start_shutdown')
                elif signal_number == signal.SIGHUP:
                    logger.debug(f'received SIGHUP, running start_shutdown')
                self._start_shutdown()
                break


class PinFollower:
    """Follow the state of a pin, optionally inverting the output

    Arguments::

        chip_id: the name of the chip. The command gpiodetect is helpful for identifying the chip_id.

        pin: the output pin number that will be used to follow the state of another pin.

        out_true: the pin output state when the source pin is true (default 1). Setting this to 0 inverts the output.

        out_false: the pin output state when the source pin is false (default 0). Setting this to 1 inverts the output.

        name: provide a name for the instance, probably most useful for debugging.

    Usage::

        Assuming a Raspberry Pi 3B where pin 23 is an input and pin 24 is mirroring it:

        in_pin = PinWatcher('pinctrl-bcm2835', pin=23)
        pin_mirror = PinFollower('pinctrl-bcm2835', pin=24, name='pin_mirror')
        async with trio.open_nursery() as nursery:
            nursery.start_soon(in_pin.pin_monitor)
            nursery.start_soon(pin_mirror.set_pin_level, in_pin)
    """

    def __init__(self, chip_id, pin, out_true=1, out_false=0, name=''):
        self._pin_values = {0, 1}
        self._chip_id = chip_id
        self._pin = pin
        self._name = name
        if (out_true in self._pin_values):
            self._out_true = out_true
        else:
            raise RuntimeError("out_true may only be set to 0 or 1")
        if (out_false in self._pin_values):
            self._out_false = out_false
        else:
            raise RuntimeError("out_false may only be set to 0 or 1")

    @property
    def out_true(self):
        return self._out_true

    @out_true.setter
    def out_true(self, new_out_true):
        if (new_out_true in self._pin_values):
            self._out_true = new_out_true
        else:
            raise RuntimeError("out_true may only be set to 0 or 1")

    @property
    def out_false(self):
        return self._out_false

    @out_false.setter
    def out_false(self, new_out_false):
        if (new_out_false in self._pin_values):
            self._out_false = new_out_false
        else:
            raise RuntimeError("out_false may only be set to 0 or 1")

    async def set_pin_level(self, pin_watcher):
        """Set an output pin to a level based on the state of another pin that is being watched.
        Waits for initialization from pin_watcher. 

        Based on the state (True|False) of the pin being watched, sets the output of another pin to 0 or 1.

        Arguments::
            pin_watcher: an instance of the PinWatcher class, which represents the state of the pin being watched.
        """
        with pin_watcher.cancel_on_shutdown():
            # Trio checkpoint to facilitate checking on shutdown signals
            await trio.sleep(0)
            with gpio.Chip(label=self._chip_id) as chip:
                pin_in = chip.line(self._pin)
                with pin_in.open(direction=gpio.DIRECTION_OUTPUT) as current_pin:
                    await pin_watcher.initialized.wait()
                    logger.info(
                        f'pin_watcher has been initialized, {self._name} monitoring on and off events')
                    logger.debug(
                        f'pin_watcher initial state in {self._name} is {pin_watcher.state}')
                    while True:
                        if pin_watcher.state:
                            current_pin.value = self._out_true
                            logger.debug(
                                f'in {self._name}, pin {self._pin} set to {self._out_true}')
                            pin_watcher.off_notify = event_to_watch = trio.Event()
                            await event_to_watch.wait()
                            if pin_watcher.shutting_down:
                                break
                        else:
                            current_pin.value = self._out_false
                            logger.debug(
                                f'in {self._name}, pin {self._pin} set to {self._out_false}')
                            pin_watcher.on_notify = event_to_watch = trio.Event()
                            await event_to_watch.wait()
                            if pin_watcher.shutting_down:
                                break
        logger.info(f'method set_pin_level in {self._name} has shutdown')
        if pin_watcher.shutting_down:
            return


async def monitor_pin_loop(pin_watcher):
    """An example of monitoring the state of a pin in a loop.

    In this example the loop is monitoring the state of the pin monitored by pin_watcher.
    Since the example is just a loop that sleeps between checking on the state, fast transitions will be missed.
    """
    with pin_watcher.cancel_on_shutdown():
        # Trio checkpoint to facilitate checking on shutdown signals
        await trio.sleep(0)
        await pin_watcher.initialized.wait()
        logger.info(
            f'pin_watcher has been initialized, monitor_pin_loop starting')
        pin_current = pin_watcher.state
        logger.debug(
            f'pin_watcher initial state in monitor_pin_loop is {pin_watcher.state}')
        while True:
            await trio.sleep(.1)
            if not pin_watcher.shutting_down:
                if (pin_current != pin_watcher.state):
                    pin_current = pin_watcher.state
                    logger.debug(
                        f'pin_watcher state in loop changed to {pin_watcher.state}')
                    # In this example, the state of pin_watcher is simply reported.
                    # Code that executes both for on and off could go here, or statements to execute based
                    # on weather pin_watcher.state is true or false could be conditionally selected.
                    # A loop that sleeps and then reads the pin state is not that useful and this
                    # function will more likely be used as a pattern to be implemented elsewhere.
                    # For example: this was written to be used in software that processes remote commands
                    # to be sent to a device that should not be getting new commands if a  particular
                    # hardware pin is set to true.
            else:
                break
    logger.info(f'monitor_pin_loop has shutdown')


async def func_on_trigger(pin_watcher):
    """An example of a function that is is waiting on the state of a pin to be true.
    """
    pin_watcher.on_notify = event_to_watch = trio.Event()
    await pin_watcher.initialized.wait()
    logger.info(f'pin_watcher has been initialized, func_on_trigger has started')
    while True:
        with pin_watcher.cancel_on_shutdown():
            await event_to_watch.wait()
            if not pin_watcher.shutting_down:
                logger.debug(f'func_on_trigger has executed')
                # Code to execute when the pin is true goes here.
                pin_watcher.on_notify = event_to_watch = trio.Event()
        if pin_watcher.shutting_down:
            break
    logger.info(f'func_on_trigger has shutdown')


async def func_off_trigger(pin_watcher):
    """An example of a function that is is waiting on the state of a pin to be false.
    """
    pin_watcher.off_notify = event_to_watch = trio.Event()
    await pin_watcher.initialized.wait()
    logger.info(
        f'pin_watcher has been initialized, func_off_trigger has started')
    while True:
        with pin_watcher.cancel_on_shutdown():
            await event_to_watch.wait()
            if not pin_watcher.shutting_down:
                logger.debug(f'func_off_trigger has executed')
                # Code to execute when the pin is false goes here.
                pin_watcher.off_notify = event_to_watch = trio.Event()
        if pin_watcher.shutting_down:
            break
    logger.info(f'func_off_trigger has shutdown')

# Outer and inner nurseries from https://github.com/python-trio/trio/issues/569
# Interesting example of using this technique: https://gist.github.com/miracle2k/8499df40a7b650198bbbc3038a6fb292


@asynccontextmanager
async def open_nurseries():
    async with trio.open_nursery() as daemon_nursery:
        try:
            async with trio.open_nursery() as normal_nursery:
                yield (normal_nursery, daemon_nursery)
        finally:
            daemon_nursery.cancel_scope.cancel()


async def main():
    logger.info('**** trio_asyncgpio_demo started ****')

    # Watch the state of pin 23 on a Raspberry Pi 3B
    in_pin = PinWatcher('pinctrl-bcm2835', pin=23)
    # Have the state of pin 23 mirrored on pin 24
    pin_mirror = PinFollower('pinctrl-bcm2835', pin=24, name='pin_mirror')
    # Have the state of pin 23 inverted on pin 26
    pin_invert = PinFollower(
        'pinctrl-bcm2835', pin=26, out_true=0, out_false=1, name='pin_invert')

    async with open_nurseries() as nurseries:
        nursery, daemon = nurseries
        daemon.start_soon(in_pin._listen_for_shutdown_signals)
        nursery.start_soon(in_pin._pin_monitor)
        nursery.start_soon(func_off_trigger, in_pin)
        nursery.start_soon(func_on_trigger, in_pin)
        nursery.start_soon(pin_mirror.set_pin_level, in_pin)
        nursery.start_soon(pin_invert.set_pin_level, in_pin)
        nursery.start_soon(monitor_pin_loop, in_pin)

    logger.info('**** trio_asyncgpio_demo stopped ****')

if __name__ == "__main__":
    trio.run(main)
