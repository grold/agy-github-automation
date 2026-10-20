"""Tests for math_utils module."""
import unittest
from src.math_utils import add, multiply, divide, power, factorial

class TestMathUtils(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(-1, 1), 0)

    def test_multiply(self):
        self.assertEqual(multiply(3, 4), 12)
        self.assertEqual(multiply(-2, 3), -6)

    def test_divide(self):
        self.assertEqual(divide(6, 3), 2.0)
        self.assertEqual(divide(-6, 3), -2.0)
        self.assertEqual(divide(6, -3), -2.0)
        self.assertEqual(divide(-6, -3), 2.0)
        self.assertEqual(divide(0, 5), 0.0)

    def test_divide_float(self):
        self.assertEqual(divide(5, 2), 2.5)
        self.assertEqual(divide(7.5, 2.5), 3.0)
        self.assertAlmostEqual(divide(1, 3), 0.3333333333333333)

    def test_divide_by_zero(self):
        with self.assertRaises(ValueError) as context:
            divide(5, 0)
        self.assertEqual(str(context.exception), "Cannot divide by zero")

        with self.assertRaises(ValueError) as context:
            divide(5, 0.0)
        self.assertEqual(str(context.exception), "Cannot divide by zero")

        with self.assertRaises(ValueError) as context:
            divide(0, 0)
        self.assertEqual(str(context.exception), "Cannot divide by zero")

    def test_power(self):
        self.assertEqual(power(2, 3), 8)
        self.assertEqual(power(5, 0), 1)
        self.assertEqual(power(0, 5), 0)
        self.assertEqual(power(-2, 3), -8)
        self.assertEqual(power(-2, 2), 4)

    def test_power_negative_exponent(self):
        self.assertEqual(power(2, -1), 0.5)
        self.assertEqual(power(2, -2), 0.25)
        self.assertEqual(power(10, -2), 0.01)

    def test_power_fractional_exponent(self):
        self.assertEqual(power(4, 0.5), 2.0)
        self.assertEqual(power(9, 0.5), 3.0)
        self.assertAlmostEqual(power(27, 1 / 3), 3.0)

    def test_power_float_base(self):
        self.assertEqual(power(2.5, 2), 6.25)

    def test_factorial(self):
        self.assertEqual(factorial(0), 1)
        self.assertEqual(factorial(1), 1)
        self.assertEqual(factorial(2), 2)
        self.assertEqual(factorial(3), 6)
        self.assertEqual(factorial(5), 120)
        self.assertEqual(factorial(6), 720)

    def test_factorial_negative(self):
        with self.assertRaises(ValueError):
            factorial(-1)
        with self.assertRaises(ValueError):
            factorial(-10)

    def test_factorial_type_error(self):
        with self.assertRaises(TypeError):
            factorial(3.5)
        with self.assertRaises(TypeError):
            factorial(3.0)
        with self.assertRaises(TypeError):
            factorial("5")
        with self.assertRaises(TypeError):
            factorial(None)
        with self.assertRaises(TypeError):
            factorial([1, 2])
        with self.assertRaises(TypeError):
            factorial(True)
        with self.assertRaises(TypeError):
            factorial(False)

if __name__ == '__main__':
    unittest.main()

