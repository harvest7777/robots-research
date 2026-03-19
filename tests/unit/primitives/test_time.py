import pytest

from simulation.primitives import Time


def test_add_two_times():
    assert Time(3) + Time(2) == Time(5)


def test_add_zero():
    assert Time(5) + Time(0) == Time(5)


def test_add_is_commutative():
    assert Time(3) + Time(2) == Time(2) + Time(3)


def test_iadd():
    t = Time(0)
    t += Time(1)
    assert t == Time(1)
    t += Time(1)
    assert t == Time(2)


def test_sub_two_times():
    assert Time(5) - Time(2) == Time(3)


def test_sub_zero():
    assert Time(5) - Time(0) == Time(5)


def test_sub_to_zero():
    assert Time(3) - Time(3) == Time(0)


def test_advance_same_as_add():
    t = Time(4)
    dt = Time(3)
    assert t.advance(dt) == t + dt


def test_equality():
    assert Time(3) == Time(3)
    assert Time(3) != Time(4)


def test_lt():
    assert Time(1) < Time(2)
    assert not Time(2) < Time(1)
    assert not Time(2) < Time(2)


def test_le():
    assert Time(1) <= Time(2)
    assert Time(2) <= Time(2)
    assert not Time(3) <= Time(2)
