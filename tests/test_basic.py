#!/usr/bin/env
# coding=utf-8

from common import *

class TestBasic(BaseTest):
    def test_not_found(self):
        key = 'foo'
        r=s.get(key)
        self.assertEqual(r.status_code, 404)

    def test_a_file(self):
        key = 'foo'
        # set
        data='hello world'
        l = len(data)+len(key)
        r=s.put(key, data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers['X-Position'], '0,0,%d'%l)

        r=s.get('info')
        self.assertEqual(r.text, '0,%d'%l)

        # get
        r=s.get(key)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, data)

        # delete
        r=s.delete(key)
        self.assertEqual(r.status_code, 200)

        r=s.get(key)
        self.assertEqual(r.status_code, 404)

    def test_two_files(self):
        key1 = 'foo'
        key2 = 'bar'
        # set
        data1='hello world'
        l1 = len(key1)+len(data1)
        r=s.put(key1, data1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers['X-Position'], '0,0,%d'%l1)

        data2='what the hell'
        l2 = len(key2)+len(data2)
        r=s.put(key2, data2)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers['X-Position'], '0,%d,%d'%(l1, l2))

        # get
        r=s.get(key1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, data1)

        r=s.get(key2)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, data2)

        # delete
        r=s.delete(key1)
        self.assertEqual(r.status_code, 200)

        r=s.delete(key2)
        self.assertEqual(r.status_code, 200)

        # get again
        r=s.get(key1)
        self.assertEqual(r.status_code, 404)

        r=s.get(key2)
        self.assertEqual(r.status_code, 404)

    def test_rotate(self):
        key1 = 'foo'
        key2 = 'bar'
        key3 = 'baz'
        # 1MB
        self.put(key1, 1024*1024)
        self.put(key2, 1024*1024)
        self.put(key3, 1024*1024)

        r=s.get(key1)
        self.assertEqual(r.status_code, 404)

        r=s.get(key2)
        self.assertEqual(r.status_code, 404)

        r=s.get(key3)
        self.assertEqual(r.status_code, 200)

    def test_multi_files(self):
        for i in range(1, 10):
            key = 'key%d'%i
            l = self.put(key, 600*1024)

        for i, status in [(i, 404) for i in range(1, 7)] + [(i, 200) for i in range(7, 10)]:
            key = 'key%d'%i
            r=s.get(key)
            self.assertEqual(r.status_code, status)

