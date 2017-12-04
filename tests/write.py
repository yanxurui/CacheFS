import sys
import os
import shutil

num = int(sys.argv[1])
assert 0<num<20
port = 1234 + num
path = '/data/cache%d/yxr' % num
if not os.path.isdir(path):
    os.makedirs(path)

f = open(path+'/temp', 'ab')

def app(env, start_response):
    start_response('200 ok', [])
    # type of env['wsgi.input'] is cStringIO.StringI
    content = env['wsgi.input'].getvalue()
    f.write(content)
    return ['True']

import bjoern
bjoern.run(app, '0.0.0.0', port)
