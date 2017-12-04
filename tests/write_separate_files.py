import sys
import os
import shutil

num = int(sys.argv[1])
assert 0<num<20
port = 1234 + num
path = '/data/cache%d/yxr' % num
if not os.path.isdir(path):
    os.makedirs(path)

def app(env, start_response):
    name = path + env['PATH_INFO']
    with open(name, 'w') as f:
        shutil.copyfileobj(env['wsgi.input'], f)
    start_response('200 ok', [('Content-Length', str(len(name)))])
    return name

import bjoern
bjoern.run(app, '0.0.0.0', port)
