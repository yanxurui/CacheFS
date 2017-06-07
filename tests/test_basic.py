#!/usr/bin/env
# coding=utf-8

import os

from common import *

class TestBasic(BaseTest):
    def test_get_not_found(self):
        r=self.s.get('/foo')
        self.assertEqual(r.status_code, 404)

    def test_put_and_get(self):
        # set
        data='hello world'
        l = len(data)
        r=self.s.put('/foo', data)
        self.assertEqual(r.status_code, 200)
        
        # verify redis
        r=self.r.get(MOUNT_POINT)
        self.assertEqual(r, '0,%d'%l)
        r=self.r.get('foo')
        self.assertEqual(r, '0,0,%d'%l)

        # get
        r=self.s.get('/foo')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, data)

        # delete
        r=self.s.delete('/foo')
        self.assertEqual(r.status_code, 404)
