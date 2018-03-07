import trio
import trio_gpio as gpio
"""
This script oggles a pin and watches another. The two are presumed to be connected (hardware wire).
"""


async def pling(line):
    while True:
        line.value = 1
        await trio.sleep(1)
        line.value = 0
        await trio.sleep(1)


async def main():
    async with trio.open_nursery() as n:
        with gpio.Chip(0) as c:
            with c.line(19).open(direction=gpio.DIRECTION_OUTPUT) as out_, \
                    c.line(20).open(direction=gpio.DIRECTION_INPUT) as in_:
                n.start_soon(pling, out_)
                while True:
                    print(in_.value)
                    await trio.sleep(0.3)


if __name__ == "__main__":
    trio.run(main)
