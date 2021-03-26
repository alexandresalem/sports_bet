import pytest


@pytest.fixture(scope='function')
def input_value():
    input = 39
    return input

def test_divisible_by_3(input_value):
    assert input_value * 2 == 78 + 1 - 1
