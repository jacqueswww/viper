import pytest
from pytest import raises

from vyper import compiler
from vyper.exceptions import ConstancyViolationException


fail_list = [
    """
x: num
@public
@constant
def foo() -> num:
    self.x = 5
    """,
    """
@public
@constant
def foo() -> num:
    send(0x1234567890123456789012345678901234567890, 5)
    """,
    """
@public
@constant
def foo() -> num:
    selfdestruct(0x1234567890123456789012345678901234567890)
    """,
    """
x: timedelta
y: num
@public
@constant
def foo() -> num(sec):
    self.y = 9
    return 5
    """,
    """
@public
@constant
def foo() -> num:
    x = raw_call(0x1234567890123456789012345678901234567890, "cow", outsize=4, gas=595757, value=9)
    return 5
    """,
    """
@public
@constant
def foo() -> num:
    x = create_with_code_of(0x1234567890123456789012345678901234567890, value=9)
    return 5
    """,
    """
@public
def foo(x: num):
    x = 5
    """,
    """
f:num

@public
def a (x:num)->num:
    self.f = 100
    return x+5

@constant
@public
def b():
    p: num = self.a(10)
    """,
    """
f:num

@public
def a (x:num):
    self.f = 100

@constant
@public
def b():
    self.a(10)
    """
]


@pytest.mark.parametrize('bad_code', fail_list)
def test_constancy_violation_exception(bad_code):
    with raises(ConstancyViolationException):
        compiler.compile(bad_code)
