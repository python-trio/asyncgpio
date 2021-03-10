asyncgpio
=========

AsyncGPIO allows easy access to the GPIO pins on your Raspberry Pi or
similar embedded computer.

It is based on libgpiod and its CFFI adapter by Steven P. Goldsmith
<sgjava@gmail.com>, as downloaded from
`github <https://github.com/sgjava/userspaceio.git>`_.

To run examples, make sure to install `trio` first.

Testing AsyncGPIO requires a Linux distribution that enables the mock-GPIO module.
As of mid-2020, Debian's kernel does not include this module, but Raspbian's does.

If you can compile your own kernel: the option is named CONFIG_GPIO_MOCKUP,
in Device Drivers / GPIO support / Memory mapped GPIO drivers / GPIO
Testing Driver.

Writing an actual test suite is TODO. There is a more elaborate test script
in `DistKV-GPIO <https://github.com/smurfix/distgpio>`_.
