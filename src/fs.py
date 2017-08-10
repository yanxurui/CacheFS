import os
from time import time
import logging

import config
from config import volume_num

logger = logging.getLogger(__name__)


# data structure
index = {
    # key1: (volume_id, offset, size),
    # key1: (volume_id, offset, size),
    # ...
}
# cache files for reading
files = {}
# where to write
pointer = {
    # volume_id,
    # offset,
    # file,
}
# keys waiting to be wriiten to disk
queue = []

# todo: response headers
headers = []

def get_path(filename, where = None):
    if where:
        if not (where == 'data' or where == 'index'):
            logger.warning('wrong subfolder')
        return os.path.join(config.mount_point, where, str(filename))
    return os.path.join(config.mount_point, str(filename))


def get_file(volume_id):
    f = files.get(volume_id, None)
    if not f:
        try:
            f = open(get_path(volume_id, 'data'), 'rb')
        except IOError:
            return None
        files[volume_id] = f
    return f


def read_index(volume_id):
    result = {}
    try:
        f = open(get_path(volume_id, 'index'))
    except IOError as e:
        logger.info('volume %d does not exist', volume_id)
        return None
    for line in f:
        key, offset, size = line.split(' ')
        if size == 0:
            del result[key]
        result[key] = (volume_id, int(offset), int(size))
    return result


def setUp():
    # restore write point
    try:
        with open(get_path('META.txt')) as meta:
            volume_id = int(meta.read())
    except IOError:
        logger.warning('META file lost')
        logger.info('build directory structure in %s' % config.mount_point)
        os.makedirs(get_path('', 'data'))
        os.makedirs(get_path('', 'index'))
        volume_id = 0
    logger.info('start writing into volume %d' % volume_id)
    pointer['volume_id'] = volume_id
    pointer['offset'] = 0
    pointer['file'] = open(get_path(pointer['volume_id'], 'data'), 'wb')
    
    # todo
    volume_id = (volume_id + 1) % volume_num
    while(volume_id != pointer['volume_id']):
        logger.info('load index for volume %d' % volume_id)
        idx = read_index(volume_id)
        if idx:
            for k, v in idx.items():
                index[k] = v
        else:
            if volume_id == 0:
                break
            else:
                volume_id = 0
                continue
        volume_id = (volume_id + 1) % volume_num



def update_index():
    volume_id = pointer['volume_id']
    s = time()
    # append index
    with open(get_path(volume_id, 'index'), 'w') as f:
        tmp = []
        for key in queue:
            pos = index.get(key, None)
            logger.debug('append index for key: %s' % key)
            # deleted just now
            if not pos:
                continue
            # key offset size\n
            tmp.append('%s %d %d'%(key, pos[1], pos[2]))
        f.write('\n'.join(tmp))
    
    logger.info('append index for volume %d cost %fs' % (volume_id, time() - s))

    # todo: close file costs too much time
    s = time()
    pointer['file'].close()
    logger.info('close file cost %fs' % (time() - s))

    volume_id = (volume_id + 1) % volume_num
    logger.info('rotate to volume %d' % volume_id)

    s = time()
    idx = read_index(volume_id)
    if idx:
        for k in idx.keys():
            del index[k]
        logger.info('delete %d keys' % len(idx))
        os.remove(get_path(volume_id, 'index'))
    logger.info('delete index of old volume %d cost %fs' % (volume_id, time() - s))

    # update write point
    with open(get_path('META.txt'), 'w') as meta:
        meta.write(str(volume_id))

    pointer['file'] = open(get_path(volume_id, 'data'), 'wb')
    pointer['volume_id'] = volume_id
    pointer['offset'] = 0

    # clear queue
    # https://stackoverflow.com/questions/850795/different-ways-of-clearing-lists
    del queue[:] # or queue[:] = []
    # files.pop(volume_id, None)


def get(key):
    pos = index.get(key, None)
    if not pos:
        return 404, 'not found'
    volume_id, offset, size = pos
    f = get_file(volume_id)
    f.seek(offset, 0)
    content = f.read(size)
    key_len = len(key)
    assert(content[:key_len] == key)
    headers.append(('X-Position', ','.join(map(str, pos))))
    # todo: optimise
    return 200, content[key_len:]


def put(key, data):
    f = pointer['file']
    # todo: optimise
    try:
        f.write(key+data)
    except ValueError as e:
        print(e)
        exit(0)
    f.flush()
    offset = pointer['offset']
    length = len(key) + len(data)
    pos = (pointer['volume_id'], offset, length)
    index[key] = pos
    headers.append(('X-Position', ','.join(map(str, pos))))
    queue.append(key)

    offset = offset + length
    assert(offset == f.tell())
    pointer['offset'] = offset
    if offset >= config.volume_size:
        update_index()
    return 200, 'ok'


def delete(key):
    pos = index.pop(key, None)
    volume_id = pos[0]
    if not pos:
        return 404, 'not found'
    if volume_id != pointer['volume_id']:
        # append a record at the end of index if the file is not in current volume
        with open(get_path(volume_id, 'index'), 'a') as f:
            # size 0 means deleted
            f.write("\n%s 0 0 0" % key)    
        
    return 200, 'ok'


def tearDown():
    for f in files.values():
        f.close()
    pointer['file'].close()


logger.info('setup...')
logger.info('volume_size: %d, volume_num: %d' % (config.volume_size, volume_num))
s = time()
setUp()
logger.info('setup done cost %fs' % (time() - s))

