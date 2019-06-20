import anyio
import asyncgpio as gpio
"""
This script oggles a pin and watches another. The two are presumed to be connected (hardware wire).
"""


async def pling(line):
    while True:
        await anyio.sleep(1)
        line.value = 1
        await anyio.sleep(1)
        line.value = 0


async def main():
    async with anyio.create_task_group() as n:
        with gpio.Chip(0) as c:
            with c.line(19).open(direction=gpio.DIRECTION_OUTPUT) as out_:
                in_ = c.line(20)
                await n.spawn(pling, out_)
                with in_.monitor(gpio.REQUEST_EVENT_BOTH_EDGES):
                    async for e in in_:
                        print(e, "on" if e.value else "off", "at", e.time.strftime("%H:%M:%S"))


if __name__ == "__main__":
    anyio.run(main, backend="trio")
