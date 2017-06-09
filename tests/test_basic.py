#!/usr/bin/env
# coding=utf-8

from common import *

class TestBasic(BaseTest):
    def test_not_found(self):
        key = 'foo'
        r=self.s.get(key)
        self.assertEqual(r.status_code, 404)

    def test_a_file(self):
        key = 'foo'
        # set
        data='hello world'
        l = len(data)+len(key)+2+3
        r=self.s.put(key, data)
        self.assertEqual(r.status_code, 200)
        
        # verify redis
        r=self.r.get(MOUNT_POINT)
        self.assertEqual(r, '0,%d,0'%l)
        r=self.r.get(key)
        self.assertEqual(r, '0,0,%d'%l)

        # get
        r=self.s.get(key)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, data)

        # delete
        r=self.s.delete(key)
        self.assertEqual(r.status_code, 200)

        r=self.s.get(key)
        self.assertEqual(r.status_code, 404)

    def test_two_files(self):
        key1 = 'foo'
        key2 = 'bar'
        # set
        data1='hello world'
        l1 = len(key1)+len(data1)+2+3
        r=self.s.put(key1, data1)
        self.assertEqual(r.status_code, 200)

        data2='what the hell'
        l2 = len(key2)+len(data2)+2+3
        r=self.s.put(key2, data2)
        self.assertEqual(r.status_code, 200)

        # verify redis
        r=self.r.get(MOUNT_POINT)
        self.assertEqual(r, '0,%d,0'%(l1+l2))

        r=self.r.get(key1)
        self.assertEqual(r, '0,0,%d'%l1)

        r=self.r.get(key2)
        self.assertEqual(r, '0,%d,%d'%(l1, l2))

        # get
        r=self.s.get(key1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, data1)

        r=self.s.get(key2)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, data2)

        # delete
        r=self.s.delete(key1)
        self.assertEqual(r.status_code, 200)

        r=self.s.delete(key2)
        self.assertEqual(r.status_code, 200)

        # get again
        r=self.s.get(key1)
        self.assertEqual(r.status_code, 404)

        r=self.s.get(key2)
        self.assertEqual(r.status_code, 404)

    def test_rotate(self):
        key1 = 'foo'
        key2 = 'bar'
        key3 = 'baz'
        # 1MB
        self.put(key1, 1024*1024)
        self.put(key2, 1024*1024)
        self.put(key3, 1024*1024)

        r=self.s.get(key1)
        self.assertEqual(r.status_code, 404)

        r=self.s.get(key2)
        self.assertEqual(r.status_code, 200)

        r=self.s.get(key3)
        self.assertEqual(r.status_code, 200)

    def test_multi_files(self):
        for i in range(1, 10):
            key = 'key%d'%i
            l = self.put(key, 600*1024)

        r=self.s.get('key4')
        self.assertEqual(r.status_code, 404)

        r=self.s.get('key5')
        self.assertEqual(r.status_code, 404)

        r=self.s.get('key6')
        self.assertEqual(r.status_code, 200)

        r=self.s.get('key9')
        self.assertEqual(r.status_code, 200)
