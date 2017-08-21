# CacheFS
A key-value store for caching huge amount of data especially small files no more than 1M. It's written in python using Jonas Haag's awesome [bjoern](https://github.com/jonashaag/bjoern) and can be easily scaled by nginx.


## Usage
### quick start
clone this project to somewhere and install dependences(you'd better do this in a virtual env):
```
# todo
pip install -r requirements.txt
```
start up using default config
```
python src/app.py
```
that's it, test by curl:
```
curl -X PUT localhost:1234/foo -d $'hello world\n'
curl localhost:1234/foo
curl -X DELETE localhost:1234/foo
curl localhost:1234/foo
```

### configuration
Config file is src/config.py. It's recommended to create a custom config file based on this file and then pass its path as argument to app.py
```
cp src/config.py config_1.py
# modify config_1.py
python src/app.py config_1.py
```

### use memcache as a LRU cache
Memcache can speed up a lot compared with pure disk access.
CacheFS is default a simple FIFO cache which is not useful in many cases. With the help of memcache, the most frequently accessed files are cached in memory even if they are erased from disk due to a very long existence time.

Turn on memcache by setting memc_on to True in config file.

A file is cached in memcache after it is missed a certain number of times during a period of time. These are configured by `cache_after_miss_count` and `cache_after_miss_count_duration`.

### scale by nginx
The best way to scale horizontally is using nginx as a reverse proxy which redirects requests to back CacheFSs based on consistency hash method. Every CacheFS is in charge of a disk mount point.
![todo]()


## API
Only these 3 apis are supported now.
### set
#### Req
PUT /<key> request body is file content

#### Resp
* 200: file is stored

custome headers

* **X-Position**: <volume_id>,<offset>,<size>

### get
GET /<key>

* 200: response body is file content
* 404: file does not exist

custom headers

* **X-Position**: the same as above
* **X-Cache**:
   * MEMC: file is hit in memcache
   * DISK: file is retrived from disk

### delete
#### Req
DELETE /<key>

#### Resp
* 200: file is deleted
* 404: file does not exist


## Implementation
### data structure
All files are stored under path <mount_point> which is a directory in a real file system.
```
├── data
│   ├── 0
│   ├── 1
│   └── 2
├── index
│   ├── 0
│   └── 2
└── META.txt
```

Inspired by [seaweedfs](https://github.com/chrislusf/seaweedfs), small files as long as their filenames(for consistency check) are stored in a big file which is called volume. Why?

1. Modern file systems for example ext4 use tree structure to organize files. It will take considerable time to look for a specific file in a large number of small files(tens of millions).
2. It must be emphasized that it takes much more time to open and close file than real raed or write. So the first principle is avoiding frequently opening and closing files for every read or write. 

Every volume file under data subfolder has its corresponding index file under index subfolder. Every line in index file is in form of `<key> <offset> <size>` which reveals where a file is stored in the volume. If a file is deleted, a line `<key> 0 0` is appended to the index file.

META.txt is used to record the id of the current volume to write data into.

When server starts up, index are built up in a big dict by scaning these index files.

### write & read & delete
Data is written cyclically from volume 0 and in a volume small files are wriiten sequentially. When a volume is full, its index is dumped to disk for sake of performance. Next volume becomes the current one for writing in turn, its data(both volume and index) is erased first.

A volume file is opened only once for all subsequent reading operations. A file is retrieved by first seeking and then reading in the volume file according to the index.

When a file is deleted, it's not actually removed from disk but just marked as deleted by appending a line with size 0 to its index file.


## Todo
* cache
   [ ] expire
   [x] memcache
   [ ] nginx
* log
   [ ] access log
   [x] slow log
* performance
   [x] save index
   [x] close file


## Test
start server
```
python src/app.py tests/config.py
```
run tests
```
python -m unittest discover
```


## Optimise
### what about save every small file directly on disk


### file operation
It takes a lot more time to open and close a file than read and write. So it's adivisable to open a file once and not to close it until all subsequent write and read are completed. 
When performing file operations in python, it's preferable to create a file object with read() and write() methods by the built-in `open` function. This works well until I find that it takes too much time to close a big file. This can be solved by replacing file object by `os` module's system call which is intended for low-level I/O.
It shows the difference below when write 1GB file:
```python
import os
from time import time

data = 'x'*1024

f = open('temp', 'w')

s1 = time()
for i in range(1000000):
    f.write(data)
    f.flush()

s2 = time()
print('write: %f' % (s2-s1))
# 2.57

f.close()
s3 = time()
print('close: %f' % (s3-s2))
# 5.65

```
```python
import os
from time import time

data = 'x'*1024

# fd = os.open("temp", os.O_CREAT | os.O_WRONLY | os.O_NONBLOCK)
fd = os.open("temp", os.O_CREAT | os.O_WRONLY)

s1 = time()
for i in range(1000000):
    os.write(fd, data)

s2 = time()
print('write: %f' % (s2-s1))
# 1.9

os.close(fd)
s3 = time()
print('close: %f' % (s3-s2))
# 0

```

Further more, one file object opened for reading can not see the new change made by another file object opened for writing unless the latter calls `flush()` after `write` which introduces extra overhead. However, system call performs well.
```python
f1 = open('a.txt', 'w')
f2 = open('a.txt')

f1.write('hello')
print(f2.read(5))
f1.flush()
print(f2.read(5))
```

```python
import os

fd_w = os.open("temp", os.O_CREAT | os.O_WRONLY)
fd_r = os.open("temp", os.O_RDONLY)

os.write(fd_w, 'hello world')

print(os.read(fd_r, 5))

```
In a short word, performance is improved a lot by using os's low-level IO operation instead of file object.

### log
Every log message means a write operation so it must be taken into account. Benchmark shows that log impacts a lot in such high-performance application scenario.
For example, consider the huge difference in `Requests/sec` below:
```python
def app(e, s):
    body = 'hello world'
    s('200 OK', [('Content-Length', str(len(body)))])
    return body

import bjoern
bjoern.run(app, '0.0.0.0', 1234)

```
```
[root@localhost wrk-4.0.2]# ./wrk -c 20 -t 1 http://127.0.0.1:1234
Running 10s test @ http://127.0.0.1:1234
  1 threads and 20 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   205.66us   26.89us   1.20ms   61.30%
    Req/Sec    97.23k    12.19k  121.01k    72.28%
  975283 requests in 10.10s, 68.83MB read
Requests/sec:  96565.62
Transfer/sec:      6.81MB
```

```python
import logging
logging.basicConfig(filename = 'test.log', format='%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s', level=logging.INFO)

def app(e, s):
    logging.info('log me')
    body = 'hello world'
    s('200 OK', [('Content-Length', str(len(body)))])
    return body

import bjoern
bjoern.run(app, '0.0.0.0', 1234)

```
```
[root@localhost wrk-4.0.2]# ./wrk -c 20 -t 1 http://127.0.0.1:1234
Running 10s test @ http://127.0.0.1:1234
  1 threads and 20 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.39ms  154.22us   9.53ms   99.39%
    Req/Sec    14.45k   206.78    14.96k    91.09%
  145224 requests in 10.10s, 10.25MB read
Requests/sec:  14378.22
Transfer/sec:      1.01MB
```

So it's a good practice to set log level to `WARNING` in production.


## Benchmark

**write and read a file with size of 200KB**

### write

#### STA
`./wrk -c 20 -t 1 -s set_sta.lua http://127.0.0.1:770`

set_sta.lua
```lua
wrk.method = "POST"
wrk.body = string.rep('1', 204800)

counter = 1

request = function()
   path = "/set/test_" .. counter
   counter = counter + 1
   return wrk.format(nil, path)
end
```

qps:1041.49

latency:20.65ms


#### TFS
`./wrk -c 20 -t 1 -s set_tfs.lua http://127.0.0.1:771/v1/tfs`

set_tfs.lua
```lua
wrk.method = 'POST'
wrk.body = string.rep('0', 204800)
```

qps:1619.53

latency:13.28ms


#### CFS
`./wrk -c 20 -t 1 -s set_cfs.lua http://127.0.0.1:1234`

set_cfs.lua
```lua
wrk.method = "PUT"
wrk.body = string.rep('1', 204800)

counter = 0

request = function()
   path = "/test_" .. counter
   counter = counter + 1
   return wrk.format(nil, path)
end
```

qps:3197.52

latency:5.76ms


### read

#### STA
`./wrk -c 20 -t 1 -s get_sta.lua http://127.0.0.1:770`

get_sta.lua
```lua
wrk.method = "GET"

counter = 1

request = function()
   path = "/get/test_" .. counter
   counter = counter + 1
   return wrk.format(nil, path)
end
```

qps:1545.52

latency:20.96ms


#### TFS

It's a little hard to use different tfs key to read each time.
For convenience, I read the same key. This makes the file cached by OS and the read speed is extreamly fast.

```bash
> ls -sh a.txt
200K a.txt
> curl -X POST -d @a.txt http://127.0.0.1:771/v1/tfs
{
    "TFS_FILE_NAME": "T1pJKgBbLj1RCvBVdK"
}
```

`./wrk -c 20 -t 1 http://127.0.0.1:771/v1/tfs/T1pJKgBbLj1RCvBVdK`

qps:3906

latency:5.07ms


#### CFS
Here I use 2 methods: first read different files, then read the same file.

`./wrk -c 20 -t 1 -s get_cfs.lua http://127.0.0.1:1234`

get_cfs.lua
```lua
counter = 1

request = function()
   path = "/test_" .. counter
   counter = counter + 1
   return wrk.format(nil, path)
end
```

qps:5634.12

latency:3.53ms


`./wrk -c 20 -t 1 -d 10 http://127.0.0.1:1234/test_456`

qps:6102.34

latency:3.28ms


