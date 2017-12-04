# test the best performance of read
# generate a.txt
# python -c 'print("0"*200*1024, )' > a.txt

f = open('/data/cache2/yxr/a.txt')
size = 200*1024
data = '0'*size

def app(e, s):
    f.seek(0, 0)
    # content = f.read(size)
    content = data
    s('200 OK', [('Content-Length', str(len(content)))])
    return content

import bjoern
bjoern.run(app, '0.0.0.0', 1235)
