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

def power(base: float, exponent: int) -> float:
    """Returns base raised to the power of exponent."""
    if base == 0 and exponent < 0:
        raise ValueError("Cannot raise 0 to a negative power")
    return float(base ** exponent)

