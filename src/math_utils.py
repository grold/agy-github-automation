"""Sample math utilities module."""

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

def gcd(a: int, b: int) -> int:
    """Returns the greatest common divisor of a and b using the Euclidean algorithm."""
    if a < 0 or b < 0:
        raise ValueError("Inputs must be non-negative integers")
    while b:
        a, b = b, a % b
    return a

