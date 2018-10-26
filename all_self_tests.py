import unittest

from main import prettify_decimals, round_to_n_decimals

class TestDecimalFormatting(unittest.TestCase):

    def test_round_to_n(self):
        self.assertEqual(round_to_n_decimals(0.00000012345),    0.0000001)
        self.assertEqual(round_to_n_decimals(0.00012345),       0.0001)
        self.assertEqual(round_to_n_decimals(1234567),          1000000)

        self.assertEqual(round_to_n_decimals(0.00000012345, 3), 0.000000123)
        self.assertEqual(round_to_n_decimals(1234567, 3),       1230000)

    def test_prettify_decimals(self):
        self.assertEqual(prettify_decimals(0),   '0')
        self.assertEqual(prettify_decimals(0.0032),           '0.0032')

        self.assertEqual(prettify_decimals(0.00000000000000123456), '1.23e-15')
        self.assertEqual(prettify_decimals(0.0000000000000123456),  '1.23e-14')
        self.assertEqual(prettify_decimals(0.000000000000123456),   '1.23e-13')
        self.assertEqual(prettify_decimals(0.00000000000123456),    '0.00000000000123')
        self.assertEqual(prettify_decimals(0.0000000000123456),     '0.0000000000123')
        self.assertEqual(prettify_decimals(0.000000000123456),      '0.000000000123')
        self.assertEqual(prettify_decimals(0.00000000123456),       '0.00000000123')
        self.assertEqual(prettify_decimals(0.0000000123456),        '0.0000000123')
        self.assertEqual(prettify_decimals(0.000000123456),         '0.000000123')
        self.assertEqual(prettify_decimals(0.00000123456),          '0.00000123')
        self.assertEqual(prettify_decimals(0.0000123456),           '0.0000123')
        self.assertEqual(prettify_decimals(0.000123456),            '0.000123')
        self.assertEqual(prettify_decimals(0.00123456),             '0.00123')
        self.assertEqual(prettify_decimals(0.012345678),            '0.0123')
        self.assertEqual(prettify_decimals(0.12345678),             '0.123')
        self.assertEqual(prettify_decimals(1.2345678),              '1.235')
        self.assertEqual(prettify_decimals(12.345678),              '12.35')
        self.assertEqual(prettify_decimals(123.45678),              '123.46')
        self.assertEqual(prettify_decimals(1234.5678),              '1234.57')
        self.assertEqual(prettify_decimals(12345.6789),             '12,346')
        self.assertEqual(prettify_decimals(12345),                  '12,345')
        self.assertEqual(prettify_decimals(123456789),              '123,456,789')
        self.assertEqual(prettify_decimals(1234567890),             '1.2 billion')
        self.assertEqual(prettify_decimals(12345678901),            '12.3 billion')
        self.assertEqual(prettify_decimals(123456789012),           '123.5 billion')
        self.assertEqual(prettify_decimals(12345678901234),         '12.3 trillion')
        self.assertEqual(prettify_decimals(123456789012345),        '123.5 trillion')
        self.assertEqual(prettify_decimals(1234567890123456),       '1.23e15')
        self.assertEqual(prettify_decimals(12345678901234567),      '1.23e16')
        self.assertEqual(prettify_decimals(123456789012345678),     '1.23e17')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(TestDecimalFormatting('test_prettify_decimals'))
    suite.addTest(TestDecimalFormatting('test_round_to_n'))
    return suite

def run_all():
    runner = unittest.TextTestRunner()
    runner.run(suite())
    