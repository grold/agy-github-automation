"""Sample math utilities module."""
from math import gcd

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

def lcm(a: int, b: int) -> int:
    """Returns the least common multiple of a and b."""
    if a < 0 or b < 0:
        raise ValueError("Inputs must be non-negative integers")
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // gcd(a, b)

