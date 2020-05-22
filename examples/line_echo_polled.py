import anyio
import asyncgpio as gpio
"""
This script oggles a pin and watches another. The two are presumed to be connected (hardware wire).
"""


async def pling(line):
    while True:
        line.value = 1
        await anyio.sleep(1)
        line.value = 0
        await anyio.sleep(1)


async def main():
    async with anyio.create_task_group() as n:
        with gpio.Chip(0) as c:
            with c.line(19).open(direction=gpio.DIRECTION_OUTPUT) as out_, \
                    c.line(20).open(direction=gpio.DIRECTION_INPUT) as in_:
                await n.spawn(pling, out_)
                while True:
                    print(in_.value)
                    await anyio.sleep(0.3)


if __name__ == "__main__":
    anyio.run(main, backend="trio")
