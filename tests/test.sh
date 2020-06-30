#!/bin/sh

set -uxe
chip="gpio-mockup-A"
cur="$(pwd)"

rmmod gpio-mockup >/dev/null 2>&1 || true
if lsmod | grep -sq gpio-mockup  ; then
	echo "Could not remove the gpio-mockup module. Exiting." >&2
	exit 1
fi
modprobe gpio-mockup gpio_mockup_ranges=-1,8
cd /sys/class/gpio/
for d in gpiochip* ; do
	if test "$(cat $d/label)" = "$chip" ; then
		D=$d
		break
	fi
done
E="/sys/kernel/debug/gpio-mockup-event/$chip"
H="$(hostname | sed -e 's/\..*//')"
cd "$cur"

export PYTHONPATH=.:../asyncgpio

python3 tests/run.py $chip
