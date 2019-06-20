.. documentation master file, created by
   sphinx-quickstart on Sat Jan 21 19:11:14 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


============================================
asyncgpio: GPIO access via Trio and libgpiod
============================================

Trio-GPIO is a simple wrapper around ``libgpiod``.

You can use Trio-GPIO to
* access a GPIO chip
* get an object describing a GPIO line
* open the line for input or output
* monitor the line for events (without polling!)

Trio-GPIO only supports Linux.
It uses the "new" GPIO interface, i.e. kernel 4.5 or later is required.

.. toctree::
   :maxdepth: 2

   usage.rst
   history.rst

====================
 Indices and tables
====================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
* :ref:`glossary`
