"""Tests for the TI-85 calculator and the arithmetic sweep.

ti85.calculate: exact evaluation of whitelisted scientific expressions,
TI syntax (^ power, n! postfix), injection-safe.
mathcheck.sweep: line-anchored extraction of <expr> = <value> claims
from model output, each evaluated and compared.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src"))

import mathcheck  # noqa: E402
import ti85  # noqa: E402


def test_calculator_exact():
    assert ti85.calculate("2+2") == "4"
    assert ti85.calculate("2^10") == "1024"
    assert ti85.calculate("10!") == "3628800"
    assert ti85.calculate("ncr(49, 6)") == "13983816"
    assert ti85.calculate("sin(pi/2)") == "1"
    assert ti85.calculate("cosd(60)") == "0.5"
    assert ti85.calculate("hypot(3, 4)") == "5"
    assert ti85.calculate("10! / (3! * 7!)") == "120"


def test_calculator_safety():
    for bad in ["__import__('os')", "(lambda: 1)()", "().__class__",
                "open('/etc/passwd')"]:
        assert ti85.calculate(bad).startswith("ERROR"), bad


def test_sweep_correct_and_wrong():
    f = mathcheck.sweep("We compute $47^2 = 2209$ first.")
    assert len(f) == 1 and f[0]["match"] is True
    f = mathcheck.sweep("So $2^{10} = 1025$ exactly.")
    assert len(f) == 1 and f[0]["match"] is False
    assert f[0]["computed"] == "1024"


def test_sweep_line_anchored():
    text = ("Step 1: 47^2 = 2209 mod 191\n"
            "2209 - (11 * 191) = 108\n"
            "Step 2: 96 * 47 = 4512 mod 191\n"
            "4512 - (23 * 191) = 119")
    f = mathcheck.sweep(text)
    assert len(f) == 4
    assert all(x["match"] for x in f)


def test_sweep_functions_and_mod():
    f = mathcheck.sweep("So $2209 \\pmod{191} = 37$.")
    assert len(f) == 1 and f[0]["match"] is False
    assert f[0]["computed"] == "108"
    f = mathcheck.sweep("And $\\binom{10}{3} = 120$ combinations.")
    assert len(f) == 1 and f[0]["match"] is True


def test_sweep_frac_and_factorial():
    f = mathcheck.sweep(
        "The probability is $\\frac{120}{1024} = 0.1171875$.")
    assert len(f) == 1 and f[0]["match"] is True
    f = mathcheck.sweep("Thus $10! = 3628800$.")
    assert len(f) == 1 and f[0]["match"] is True
