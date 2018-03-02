import trio

# We can just use 'async def test_*' to define async tests.
# This also uses a virtual clock fixture, so time passes quickly and
# predictably.
async def test_basic_import():
    from trio_gpio import gpio
    assert gpio.Card
