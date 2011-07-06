from decimal import Decimal
import unittest

from django_easyfilters.ranges import auto_ranges


class TestRanges(unittest.TestCase):

    def test_auto_ranges_simple(self):
        """
        Test that auto_ranges produces 'nice' looking automatic ranges.
        """
        # An easy case - max_items is just what we want
        ranges1 = auto_ranges(Decimal('15.0'), Decimal('20.0'), 5)
        self.assertEqual(ranges1,
                         [(Decimal('15.0'), Decimal('16.0')),
                          (Decimal('16.0'), Decimal('17.0')),
                          (Decimal('17.0'), Decimal('18.0')),
                          (Decimal('18.0'), Decimal('19.0')),
                          (Decimal('19.0'), Decimal('20.0'))])

    def test_auto_ranges_flexible_max_items(self):
        # max_items is a bit bigger than what we want,
        # but we should be flexible if there is an easy target.
        ranges1 = auto_ranges(Decimal('15.0'), Decimal('20.0'), 6)
        self.assertEqual(ranges1,
                         [(Decimal('15.0'), Decimal('16.0')),
                          (Decimal('16.0'), Decimal('17.0')),
                          (Decimal('17.0'), Decimal('18.0')),
                          (Decimal('18.0'), Decimal('19.0')),
                          (Decimal('19.0'), Decimal('20.0'))])

    def test_auto_ranges_round_limits(self):
        # start and end limits should be rounded to something nice

        # Check with 5-10, 50-100, 15-20, 150-200

        ranges1 = auto_ranges(Decimal('15.1'), Decimal('19.9'), 5)
        self.assertEqual(ranges1,
                         [(Decimal('15.0'), Decimal('16.0')),
                          (Decimal('16.0'), Decimal('17.0')),
                          (Decimal('17.0'), Decimal('18.0')),
                          (Decimal('18.0'), Decimal('19.0')),
                          (Decimal('19.0'), Decimal('20.0'))])

        ranges2 = auto_ranges(Decimal('151'), Decimal('199'), 5)
        self.assertEqual(ranges2,
                         [(Decimal('150'), Decimal('160')),
                          (Decimal('160'), Decimal('170')),
                          (Decimal('170'), Decimal('180')),
                          (Decimal('180'), Decimal('190')),
                          (Decimal('190'), Decimal('200'))])

        ranges3 = auto_ranges(Decimal('5.1'), Decimal('9.9'), 5)
        self.assertEqual(ranges3,
                         [(Decimal('5.0'), Decimal('6.0')),
                          (Decimal('6.0'), Decimal('7.0')),
                          (Decimal('7.0'), Decimal('8.0')),
                          (Decimal('8.0'), Decimal('9.0')),
                          (Decimal('9.0'), Decimal('10.0'))])

        ranges4 = auto_ranges(Decimal('51'), Decimal('99'), 5)
        self.assertEqual(ranges4,
                         [(Decimal('50'), Decimal('60')),
                          (Decimal('60'), Decimal('70')),
                          (Decimal('70'), Decimal('80')),
                          (Decimal('80'), Decimal('90')),
                          (Decimal('90'), Decimal('100'))])

        ranges5 = auto_ranges(Decimal('3'), Decimal('6'), 5)
        self.assertEqual(ranges5,
                         [(Decimal('3'), Decimal('4')),
                          (Decimal('4'), Decimal('5')),
                          (Decimal('5'), Decimal('6'))])

    def test_auto_ranges_type(self):
        """
        auto_ranges should return the same type of thing it is passed
        """
        r = auto_ranges(1, 10, 10)
        self.assertEqual(type(r[0][0]), int)

        r2 = auto_ranges(Decimal('1'), Decimal('10'), 10)
        self.assertEqual(type(r2[0][0]), Decimal)
