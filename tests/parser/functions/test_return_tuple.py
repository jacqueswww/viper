import pytest
from tests.setup_transaction_tests import chain as s, tester as t, ethereum_utils as u, check_gas, \
    get_contract_with_gas_estimation, get_contract


def test_return_type():
    code = """
# def out_literals() -> (num, address):
#     return 1, 0x0000000000000000000000000000000000000000

def out_bytes(x: num, y: bytes <= 4) -> (num, bytes <= 4):
    return x, y

# def out() -> (num, bytes <= 4, bytes <= 4):
#     return 5555555, "test", "test"
    """

    c = get_contract(code)

    assert c.out_bytes(5555555, "test") == [5555555, "test"]

    # assert c.out_literals() == [1, "0x0000000000000000000000000000000000000000"]
    # assert c.out_bytes('test') == "test"
