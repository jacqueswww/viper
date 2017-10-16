import pytest
from tests.setup_transaction_tests import chain as s, tester as t, ethereum_utils as u, check_gas, \
    get_contract_with_gas_estimation, get_contract


def test_return_type():
    long_string = 65 * "test"

    code = """
def out_literals() -> (num, address):
    return 1, 0x0000000000000000000000000000000000000000

def out_bytes_a(x: num, y: bytes <= 4) -> (num, bytes <= 4):
    return x, y

def out_bytes3(x: num, y: bytes <= 4) -> (bytes <= 4, num, bytes <= 4):
    return y, x, y

# def out_bytes2(x: num, y: bytes <= 4) -> (bytes <= 4, num):
#   return y, x

# def out() -> bytes <= 4:
#    return "test"

# def out() -> (bytes <= 4, bytes <= 4):
#     return "test", "test"

def out_very_long_bytes() -> (num, bytes <= 1024, num, address):
    return 5555, "{long_string}", 6666, 0x0000000000000000000000000000000000001234
    """.format(long_string=long_string)

    c = get_contract(code)

    # assert c.out_literals() == [1, "0x0000000000000000000000000000000000000000"]
    # assert c.out_bytes_a(5555555, "test") == [5555555, b"test"]
    # assert c.out_bytes3(5555555, "test") == [5555555, 5555555, b"test"]

    # ----> works until here !!!

    # assert c.out_bytes2(5555555, "test") == [b"test", 5555555]
    # assert c.out() == b"test"

    # assert c.out() == [5555555, "test", "test"]
    # assert c.out_bytes('test') == "test"

    # assert c.out_very_long_bytes() == [5555, long_string, 6666, 0x00000000000000000000000000000000000001234]
