import logging
import traceback

from pymemcache.client.base import Client

import fs
import config
from response import Response
from counter import ExpiringCounter

logger = logging.getLogger(__name__)
counter = ExpiringCounter(config.cache_after_miss_count_duration)
# set timeout as 50ms to avoid blocking your process when memcached is slow
# The "noreply" flag is enabled by default for "set" and "delete"
client = Client((config.memc_ip, config.memc_port), timeout=0.05)


def get(key):
    try:
        v=client.get(key)
    except:
        v = None
        logger.error(traceback.format_exc())
    if v:
        return Response(200, v, headers={'X-Cache': 'MEMC'})
    resp = fs.get(key)
    if resp.status == 200:
        resp.headers['X-Cache'] = 'DISK'
        c = counter.count(key)
        logger.debug('key %s missed %d' % (key, c))
        if c >= config.cache_after_miss_count:
            counter.remove(key)
            try:
                client.set(key, resp.body)
            except:
                logger.error(traceback.format_exc())
    return resp


def put(key, data):
    try:
        client.delete(key)
    except:
        logger.error(traceback.format_exc())
    return fs.put(key, data)


def delete(key):
    try:
        client.delete(key)
    except:
        logger.error(traceback.format_exc())
    return fs.delete(key)


def flush_all():
    client.flush_all()
