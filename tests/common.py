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
import redis

# os.getenv is equivalent, and can also give a default value instead of `None`
NGX_BIN = os.getenv('NGX_BIN', '/opt/nginx/sbin/nginx')
HOST = os.getenv('URL', 'http://127.0.0.1:8082/')
URL = 'test.nfs.com'
REDIS_IP, REDIS_PORT = '127.0.0.1', 6379
MOUNT_POINT = '/data/cache2/yxr'


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


class BaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cwd = os.path.dirname(os.path.realpath(__file__))
        # backup original config.lua
        shutil.move(os.path.join(cwd, '../lua/config.lua'), os.path.join(cwd, '../lua/config.lua.bak'))
        # copy config.lua for test
        shutil.copyfile(os.path.join(cwd, 'config.lua'), os.path.join(cwd, '../lua/config.lua'))

    @classmethod
    def tearDownClass(cls):
        cwd = os.path.dirname(os.path.realpath(__file__))
        shutil.move(os.path.join(cwd, '../lua/config.lua.bak'), os.path.join(cwd, '../lua/config.lua'))

    def setUp(self):
        self.s = Session()
        self.r = redis.StrictRedis(host=REDIS_IP, port=REDIS_PORT, db=0)
        self.clean()
        time.sleep(0.1)

    def restart(self):
        try:
            out = subprocess.check_output([NGX_BIN, '-s', 'reload'], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as exc:
            print('%d\nstderr: %s' % (exc.returncode, exc.output))
            raise exc
        else:
            if out:
                print('stdout: ' + out)

    def clean(self):
        # clear redis
        self.r.flushall()
        # clear disk
        pattern = MOUNT_POINT+'/*'
        all_files = glob.glob(pattern)
        for i in all_files:
           os.remove(i)
        # reload nginx config
        self.restart()

    def put(self, key, size):
        data = '0'*size
        r=self.s.put(key, data)
        self.assertEqual(r.status_code, 200)
        k_len = len(key)
        return len(str(k_len))+k_len+len(str(size))+size


