import os
from time import time
import shutil
import logging

import config
from response import Response

logging.basicConfig(filename = config.log_file, format='%(asctime)s %(levelname)s %(filename)s:%(lineno)d:%(message)s', level=getattr(logging, config.log_level))

import fs

logger = logging.getLogger(__name__)

def app(env, start_response):
    s = time()

    method = env['REQUEST_METHOD']
    logger.info('%s %s' % (method, env['PATH_INFO']))

    key = env['PATH_INFO'][1:]
    if not key:
        resp = Response(400)
    elif key == 'info':
        # todo: use signal
        resp = Response(body='%d,%d' % (fs.pointer['volume_id'], fs.pointer['offset']))
    elif key == 'flush':
        fs.tearDown()
        logger.warning('delete all files in disk')
        shutil.rmtree(config.mount_point)
        # reload config first
        reload(config)
        reload(fs)
        resp = Response()
    elif method == 'GET':
        resp = fs.get(key)
    elif method == 'PUT':
        data = env['wsgi.input'].getvalue()
        if not data:
            status = 400
        resp = fs.put(key, data)
    elif method == 'DELETE':
        resp = fs.delete(key)
    else:
        resp = Response(501)

    elapsed = time()-s
    if elapsed > config.log_slow:
        logger.warn('%s %s %d %fs' % (method, env['PATH_INFO'], status, time()-s))

    start_response(resp.get_status(), resp.get_headers())
    return resp.body

    

logger.info('listening at %s:%d' % (config.ip, config.port))

import bjoern
bjoern.run(app, config.ip, config.port)
