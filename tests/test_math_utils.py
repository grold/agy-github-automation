"""Tests for math_utils module."""
import unittest
from src.math_utils import add, multiply, divide, lcm

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

    def test_lcm(self):
        self.assertEqual(lcm(4, 6), 12)
        self.assertEqual(lcm(6, 4), 12)
        self.assertEqual(lcm(3, 5), 15)
        self.assertEqual(lcm(12, 18), 36)
        self.assertEqual(lcm(7, 7), 7)
        self.assertEqual(lcm(1, 1), 1)
        self.assertEqual(lcm(1, 10), 10)
        self.assertEqual(lcm(10, 1), 10)
        self.assertEqual(lcm(3, 9), 9)
        self.assertEqual(lcm(21, 6), 42)
        self.assertIsInstance(lcm(4, 6), int)

    def test_lcm_with_zero(self):
        self.assertEqual(lcm(0, 5), 0)
        self.assertEqual(lcm(5, 0), 0)
        self.assertEqual(lcm(0, 0), 0)
        self.assertIsInstance(lcm(0, 5), int)
        self.assertIsInstance(lcm(0, 0), int)

    def test_lcm_negative_inputs(self):
        with self.assertRaises(ValueError) as context:
            lcm(-1, 5)
        self.assertEqual(str(context.exception), "Inputs must be non-negative integers")

        with self.assertRaises(ValueError) as context:
            lcm(5, -1)
        self.assertEqual(str(context.exception), "Inputs must be non-negative integers")

        with self.assertRaises(ValueError) as context:
            lcm(-4, -6)
        self.assertEqual(str(context.exception), "Inputs must be non-negative integers")

if __name__ == '__main__':
    unittest.main()

