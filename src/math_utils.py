"""Sample math utilities module."""

import math

def add(a: float, b: float) -> float:
    """Returns the sum of a and b."""
    return a + b

def multiply(a: float, b: float) -> float:
    """Returns the product of a and b."""
    return a * b

def divide(a: float, b: float) -> float:
    """Returns the quotient of a and b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def power(base: float, exponent: float) -> float:
    """Returns base raised to the power of exponent."""
    return base ** exponent

def factorial(n: int) -> int:
    """Returns the factorial of a non-negative integer n."""
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("Factorial is only defined for integers")
    if n < 0:
        raise ValueError("Factorial is not defined for negative values")
    return math.factorial(n)

