import unittest
import time

from src.counter import ExpiringCounter

class TestCounter(unittest.TestCase):
    def assertEqual(self, a, b):
        if type(a) is not list and type(b) is list:
            self.assertEqual(list(a), b)

    def assertItemsEqual(self, a, b):
        self.assertEqual(sorted(a), sorted(b))

    def setUp(self):
        self.counter = ExpiringCounter(.3)

    def test_count_one(self):
        # add and count
        self.counter.count('foo')
        self.assertEqual(self.counter.keys(), ['foo'])
        self.assertEqual(self.counter.values(), [1])
        self.assertEqual(self.counter.items(), [('foo', 1)])
        self.assertTrue(self.counter.has_key('foo'))

        # count again
        self.counter.count('foo', 2)
        self.assertEqual(self.counter.values(), [3])
        self.assertEqual(self.counter.items(), [('foo', 3)])

        # remove
        self.counter.remove('foo')
        self.assertEqual(self.counter.keys(), [])
        self.assertEqual(self.counter.values(), [])
        self.assertEqual(self.counter.items(), [])
        self.assertFalse(self.counter.has_key('foo'))

    def test_count_multiple(self):
        # add and count
        self.counter.count('foo')
        self.counter.count('bar', 2)
        self.assertItemsEqual(self.counter.keys(), ['foo', 'bar'])
        self.assertItemsEqual(self.counter.items(), [('foo', 1), ('bar', 2)])
        self.assertTrue(self.counter.has_key('foo'))
        self.assertTrue(self.counter.has_key('bar'))

        v=self.counter.count('baz')
        self.assertEqual(v, 1)
        self.assertItemsEqual(self.counter.keys(), ['foo', 'bar', 'baz'])

    def test_expire(self):
        # add and count
        self.counter.count('foo')
        self.counter.count('bar')
        time.sleep(0.2)
        v=self.counter.count('foo')
        time.sleep(0.2)
        self.assertTrue(self.counter.has_key('foo'))
        self.assertFalse(self.counter.has_key('bar'))

