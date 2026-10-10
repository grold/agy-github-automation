"""Tests for math_utils module."""
import unittest
from src.math_utils import add, multiply, divide, gcd

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

    def test_gcd(self):
        self.assertEqual(gcd(48, 18), 6)
        self.assertEqual(gcd(18, 48), 6)
        self.assertEqual(gcd(20, 8), 4)
        self.assertEqual(gcd(54, 24), 6)
        self.assertEqual(gcd(7, 13), 1)
        self.assertEqual(gcd(1, 1), 1)
        self.assertEqual(gcd(12, 12), 12)
        self.assertEqual(gcd(100, 10), 10)

    def test_gcd_with_zero(self):
        self.assertEqual(gcd(0, 5), 5)
        self.assertEqual(gcd(5, 0), 5)
        self.assertEqual(gcd(0, 0), 0)

    def test_gcd_large_numbers(self):
        self.assertEqual(gcd(1071, 462), 21)
        self.assertEqual(gcd(1000000000, 500000000), 500000000)

    def test_gcd_negative_numbers(self):
        with self.assertRaises(ValueError) as context:
            gcd(-1, 5)
        self.assertEqual(str(context.exception), "Inputs must be non-negative integers")

        with self.assertRaises(ValueError) as context:
            gcd(5, -1)
        self.assertEqual(str(context.exception), "Inputs must be non-negative integers")

        with self.assertRaises(ValueError) as context:
            gcd(-5, -5)
        self.assertEqual(str(context.exception), "Inputs must be non-negative integers")

        with self.assertRaises(ValueError) as context:
            gcd(-1, 0)
        self.assertEqual(str(context.exception), "Inputs must be non-negative integers")

        with self.assertRaises(ValueError) as context:
            gcd(0, -1)
        self.assertEqual(str(context.exception), "Inputs must be non-negative integers")

if __name__ == '__main__':
    unittest.main()

