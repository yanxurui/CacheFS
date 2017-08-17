#!/usr/bin/env
# coding=utf-8

import subprocess
import os
import json
import unittest
import glob
import time
import shutil

import requests


HOST = os.getenv('URL', 'http://127.0.0.1:1235/')


class Session(requests.Session):
    # In Python 3 you could place `url_base` after `*args`, but not in Python 2.
    def __init__(self, url_base=HOST, *args, **kwargs):
        super(Session, self).__init__(*args, **kwargs)
        self.url_base = url_base

    def request(self, method, url, **kwargs):
        # Next line of code is here for example purposes only.
        # You really shouldn't just use string concatenation here,
        # take a look at urllib.parse.urljoin instead.
        modified_url = self.url_base + url
        return super(Session, self).request(method, modified_url, **kwargs)

s = Session()

class BaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cwd = os.path.dirname(os.path.realpath(__file__))
        # backup original config.py
        shutil.move(os.path.join(cwd, '../src/config.py'), os.path.join(cwd, '../src/config.py.bak'))
        # copy config.py for test
        shutil.copyfile(os.path.join(cwd, 'config.py'), os.path.join(cwd, '../src/config.py'))

    @classmethod
    def tearDownClass(cls):
        cwd = os.path.dirname(os.path.realpath(__file__))
        shutil.move(os.path.join(cwd, '../src/config.py.bak'), os.path.join(cwd, '../src/config.py'))

    def setUp(self):
        # clear data & reload config
        r=s.get('flush')
        self.assertEqual(r.status_code, 200)
        time.sleep(0.1)

    def put(self, key, size):
        data = '0'*size
        r=s.put(key, data)
        self.assertEqual(r.status_code, 200)


