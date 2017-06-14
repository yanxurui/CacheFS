import os
from time import time
import shutil
import logging

import config

logging.basicConfig(filename = config.log_file, format='%(asctime)s %(levelname)s %(name)s:%(lineno)d:%(message)s', level=getattr(logging, config.log_level))

import fs

STATUS = {
    200: '200 OK',
    400: '400 Bad Request',
    404: '404 Not Found',
    500: 'Internal Server Error',
    501: '501 Not Implemented',
}

logger = logging.getLogger(__name__)

def app(env, start_response):
    status = 200
    body = ''

    method = env['REQUEST_METHOD']
    logger.info('%s %s' % (method, env['PATH_INFO']))
    s = time()

    key = env['PATH_INFO'][1:]
    if not key:
        status = 400
    elif key == 'info':
        # todo: use signal
        body = '%d,%d' % (fs.pointer['volume_id'], fs.pointer['offset'])
    elif key == 'flush':
        fs.tearDown()
        logger.warning('delete all files in disk')
        shutil.rmtree(config.mount_point)
        # reload config first
        reload(config)
        reload(fs)
    elif method == 'GET':
        status, body = fs.get(key)
    elif method == 'PUT':
        data = env['wsgi.input'].getvalue()
        if not data:
            status = 400
        status, body = fs.set(key, data)
    elif method == 'DELETE':
        status, body = fs.delete(key)
    else:
        status = 501

    logger.info('%s %s %d %f' % (method, env['PATH_INFO'], status, time()-s))

    headers = fs.headers
    headers.append(('Content-Length', str(len(body))))
    start_response(STATUS[status], headers)
    fs.headers = []
    return body

    

logger.info('listening at %s:%d' % (config.ip, config.port))

import bjoern
bjoern.run(app, config.ip, config.port)
