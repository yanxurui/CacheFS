#!/usr/bin/env
# coding=utf-8

from common import *

class TestMemc(BaseTest):
    def test_a_file(self):
        # set
        k = 'foo'
        self.put(k, 100)

        # get&miss
        r=s.get(k)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers['X-Cache'], 'DISK')
        r=s.get(k)
        self.assertEqual(r.headers['X-Cache'], 'DISK')
        
        # hit
        r=s.get(k)
        self.assertEqual(r.headers['X-Cache'], 'MEMC')
        r=s.get(k)
        self.assertEqual(r.headers['X-Cache'], 'MEMC')

        # delete
        s.delete(k)
        r=s.get(k)
        self.assertEqual(r.status_code, 404)


    def test_cache_condition(self):
        '''
        a file is cache before it's missed during a period of time
        '''
        k = 'foo'
        self.put(k, 100)

        r=s.get(k)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers['X-Cache'], 'DISK')
        time.sleep(0.6)
        # counter is cleared
        r=s.get(k)
        self.assertEqual(r.headers['X-Cache'], 'DISK')
        r=s.get(k)
        self.assertEqual(r.headers['X-Cache'], 'DISK')

        # now hit
        r=s.get(k)
        self.assertEqual(r.headers['X-Cache'], 'MEMC')


    def test_update(self):
        '''
        prune stale file from memcache if it is updated
        '''
        k = 'foo'
        self.put(k, 100)
        r=s.get(k)
        r=s.get(k)
        # now it's in memcache
        r=s.get(k)
        self.assertEqual(r.headers['X-Cache'], 'MEMC')

        v = 'hello world'
        r=s.put(k, v)
        self.assertEqual(r.status_code, 200)
        r=s.get(k)
        self.assertEqual(r.text, v)
        self.assertEqual(r.headers['X-Cache'], 'DISK')


