import os
from time import time
import shutil
import logging
import imp
import sys

if len(sys.argv)>1:
    config_file = sys.argv[1]
    config = imp.load_source('config', config_file)
else:
    import config
    config_file = config.__file__

logging.basicConfig(filename = config.log_file, format='%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s', level=getattr(logging, config.log_level))
logger = logging.getLogger(__name__)
logger.info('config file: %s' % config_file)

import fs
from response import Response

if config.memc_on:
    import memc
    get, put, delete = memc.get, memc.put, memc.delete
    logger.info('use memcache %s:%d' % (config.memc_ip, config.memc_port))
else:
    get, put, delete = fs.get, fs.put, fs.delete

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
        reload(fs)
        if config.memc_on:
            memc.flush_all()
        resp = Response()
    elif method == 'GET':
        resp = get(key)
    elif method == 'PUT':
        data = env['wsgi.input'].getvalue()
        if data:
            resp = put(key, data)
        else:
            resp = Response(400)
    elif method == 'DELETE':
        resp = delete(key)
    else:
        resp = Response(501)

    elapsed = time()-s
    if elapsed > config.log_slow:
        logger.warn('%s %s %d %fs' % (method, env['PATH_INFO'], resp.status, time()-s))

    start_response(resp.get_status(), resp.get_headers())
    return resp.body


if __name__ == '__main__':
    import bjoern
    logger.info('listening at %s:%d' % (config.ip, config.port))
    bjoern.run(app, config.ip, config.port)

