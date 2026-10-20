"""Tests for math_utils module."""
import unittest
from src.math_utils import add, multiply, divide, power

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

    def test_power_positive(self):
        self.assertEqual(power(2, 3), 8.0)
        self.assertEqual(power(3, 2), 9.0)
        self.assertEqual(power(-2, 3), -8.0)
        self.assertEqual(power(-2, 2), 4.0)
        self.assertEqual(power(2.5, 2), 6.25)
        self.assertEqual(power(0, 2), 0.0)

    def test_power_zero(self):
        self.assertEqual(power(2, 0), 1.0)
        self.assertEqual(power(-2, 0), 1.0)
        self.assertEqual(power(0, 0), 1.0)
        self.assertEqual(power(1.5, 0), 1.0)

    def test_power_negative(self):
        self.assertEqual(power(2, -1), 0.5)
        self.assertEqual(power(2, -2), 0.25)
        self.assertEqual(power(4, -1), 0.25)
        self.assertEqual(power(-2, -1), -0.5)
        self.assertEqual(power(-2, -2), 0.25)

    def test_power_zero_negative_exponent(self):
        with self.assertRaises(ValueError) as context:
            power(0, -1)
        self.assertEqual(str(context.exception), "Cannot raise 0 to a negative power")

        with self.assertRaises(ValueError) as context:
            power(0.0, -2)
        self.assertEqual(str(context.exception), "Cannot raise 0 to a negative power")


if __name__ == '__main__':
    unittest.main()

