Tips
====

How to test
-----------

There aren't any test cases yet. The reason is that most Linux distributions
don't ship the ``gpio-mockup`` module that would allow me to control
pseudo-GPIO pins from user space. Also, libgpiod isn't in Ubuntu stable yet.

You can run the example programs on a Raspberry Pi, if you connect the right
two pins on the expansion header.


To run yapf
-----------

* Show what changes yapf wants to make: ``yapf -rpd setup.py
  asyncgpio tests``

* Apply all changes directly to the source tree: ``yapf -rpi setup.py
  asyncgpio tests``


To make a release
-----------------

* Update the version in ``asyncgpio/_version.py``

* Run ``towncrier`` to collect your release notes.

* Review your release notes.

* Check everything in.

* Double-check it all works, docs build, etc.

* Build your sdist and wheel: ``python setup.py sdist bdist_wheel``

* Upload to PyPI: ``twine upload dist/*``

* Use ``git tag`` to tag your version.

* Don't forget to ``git push --tags``.
