import asyncgpio as gpio
import time
"""Flash an output manually.

On the Pi3, control the LEDs thus:
# cd /sys/class/leds/led0 ## or /led1
# echo gpio >trigger
# echo 16 >gpio

Enjoy.

NB: The red LED can go much faster. Have fun.
The green LED cannot (limited by hardware,
so that you can still see very fast flashes)

"""
if __name__ == "__main__":
    with gpio.Chip(0) as c:
        with c.line(16).open(gpio.DIRECTION_OUTPUT) as l:

            try:
                while True:
                    l.value = 1
                    time.sleep(0.1)
                    l.value = 0
                    time.sleep(0.1)
            finally:
                l.value = 0
