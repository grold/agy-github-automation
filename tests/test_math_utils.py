"""Tests for math_utils module."""
import unittest
from src.math_utils import add, multiply, divide, modulo

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

    def test_modulo(self):
        self.assertEqual(modulo(10, 3), 1)
        self.assertEqual(modulo(10, 5), 0)
        self.assertEqual(modulo(0, 5), 0)
        self.assertEqual(modulo(-10, 3), 2)
        self.assertEqual(modulo(10, -3), -2)
        self.assertEqual(modulo(-10, -3), -1)

    def test_modulo_by_zero(self):
        with self.assertRaises(ValueError) as context:
            modulo(10, 0)
        self.assertEqual(str(context.exception), "Cannot divide by zero")

        with self.assertRaises(ValueError) as context:
            modulo(0, 0)
        self.assertEqual(str(context.exception), "Cannot divide by zero")

        with self.assertRaises(ValueError) as context:
            modulo(-10, 0)
        self.assertEqual(str(context.exception), "Cannot divide by zero")

if __name__ == '__main__':
    unittest.main()

