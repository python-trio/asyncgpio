#!/usr/bin/make -f

PACKAGE=asyncgpio
ifneq ($(wildcard /usr/share/sourcemgr/make/py),)
include /usr/share/sourcemgr/make/py
# availabe via http://github.com/smurfix/sourcemgr

else
%:
	@echo "Please use 'python setup.py'."
	@exit 1
endif

pytest:
	sudo tests/test.sh

.PHONY: modload

