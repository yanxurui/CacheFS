# CacheFS
A key-value store for caching huge amount of data especially small files no more than 1M. It's written in python using Jonas Haag's awesome [bjoern](https://github.com/jonashaag/bjoern) and can be easily scaled by nginx.


## Usage
### quick start
clone this project to somewhere and install dependences(you'd better do this in a virtual env):
```
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


## API
Only these 3 restful APIs are supported now.
### set
#### Req
`PUT /<key>` request body is the file content

#### Resp
* 200: the file (request body) is stored

custome headers

* **X-Position**: `<volume_id>,<offset>,<size>`

### get
`GET /<key>`

* 200: response body is the file retrieved
* 404: file does not exist

custom headers

* **X-Position**: the same as above
* **X-Cache**:
   * MEMC: file is hit in memcache
   * DISK: file is retrived from disk

### delete
#### Req
`DELETE /<key>`

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

1. Modern file systems for example ext4 use tree structure to organize files. It will take considerable time to look for a specific file among a large number of small files (e.g., tens of millions).
2. It must be emphasized that it takes much more time to open and close the file than the real read or write. So the first principle is avoiding frequently opening and closing files.

Every volume file under data subfolder has its corresponding index file under index subfolder. Every line in index file is in form of `<key> <offset> <size>` which reveals where a file is stored in the volume. If a file is deleted, a line `<key> 0 0` is appended to the index file.

META.txt is used to record the id of the current volume to write data into.

When server starts up, index are built up in a big dict by scaning these index files.

### write & read & delete
Data is written cyclically starting from volume 0 and in a volume small files are wriiten sequentially. When a volume is full, its index is dumped to disk for the sake of performance. Next volume becomes the current one for writing in turn, its data (both volume and index) is erased first.

A volume file is opened only once for all subsequent reading operations. A file is retrieved by first seeking and then reading in the volume file according to the index.

When a file is deleted, it's not actually removed from disk but just marked as deleted by appending a line with size 0 to its index file.


## Todo
* cache
   - [ ] expire
   - [x] memcache
   - [ ] nginx
* log
   - [ ] access log
   - [x] slow log
* performance
   - [x] save index
   - [x] close file
   - [ ] I can not attain the performance of get api in the benchmark below


## Test
install dependencies
```
yum install memcached
systemctl start memcached

pip install requests
```

start server
```
python src/app.py tests/config.py
```

run tests
```
python -m unittest discover
```


## Optimise
<!-- ### what about save every small file directly on disk
 -->
### file operation
It takes much more time to open and close a file than read and write. So it's adivisable to open a file once and not to close it until all subsequent write and read are completed.
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
print(f2.read(5)) # hello
```

```python
import os

fd_w = os.open("temp", os.O_CREAT | os.O_WRONLY)
fd_r = os.open("temp", os.O_RDONLY)

os.write(fd_w, 'hello world')

print(os.read(fd_r, 5)) # hello

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

The results vary a lot because there are a few factors that can impact the performance:

1. the performance is bound to the **disk R/W speed**
2. the duration to observe can also affect the performance a lot because the disk usually performs much better at the first few seconds up to 500MB/s and then drops to an average speed around 50MB/s
3. file/block size * QPS ≈ disk R/W speed. For instance, there is a large difference between the QPS resulted from writing file size 1KB and 100KB.
4. read speed should be measured **after clearing cache** and **against 200 responses**

### Disk performance
Firstly, let's measure the disk W/R speed:
```
> dd if=/dev/zero of=./largefile bs=64KB count=100000
100000+0 records in
100000+0 records out
6400000000 bytes (6.4 GB) copied, 121.629 s, 52.6 MB/s

> free -h
              total        used        free      shared  buff/cache   available
Mem:           7.8G        433M        756M        427M        6.6G        6.6G
Swap:            0B          0B          0B
> sudo sh -c "sync && echo 3 > /proc/sys/vm/drop_caches"
> free -h
              total        used        free      shared  buff/cache   available
Mem:           7.8G        429M        6.9G        427M        505M        6.8G
Swap:            0B          0B          0B

> dd if=./largefile of=/dev/null bs=64k
97656+1 records in
97656+1 records out
6400000000 bytes (6.4 GB) copied, 166.517 s, 38.4 MB/s
```

Unfortunately, the disk speed is too slow, which becomes a bottleneck.


### write
file size is 64KB

set_cfs.lua
```lua
wrk.method = "PUT"
wrk.body = string.rep('1', 64000)

counter = 1

request = function()
   path = "/test_" .. counter
   counter = counter + 1
   return wrk.format(nil, path)
end
```

```
> ./wrk -c 20 -t 1 -d 30 -s set_cfs.lua http://127.0.0.1:1234

Running 30s test @ http://127.0.0.1:1234
  1 threads and 20 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    14.27ms   11.86ms  48.26ms   40.86%
    Req/Sec     1.51k     2.39k   10.63k    91.67%
  45021 requests in 30.03s, 4.08MB read
Requests/sec:   1499.45
Transfer/sec:    139.01KB
```
≈100MB/s


### read

I use 3 methods:

1. read 40 thousand files randomly

  * make sure files `test_1` ~ `test_40000` are already set after testing write above
  * clear cache at first

get_cfs1.lua
```lua
request = function()
    counter = math.random(40000)
    path = "/test_" .. counter
    return wrk.format(nil, path)
end
```

using cache
```
> free -h
              total        used        free      shared  buff/cache   available
Mem:           7.8G        426M        4.1G        427M        3.3G        6.7G
Swap:            0B          0B          0B

> ./wrk -c 20 -t 1 -d 20 -s get_cfs1.lua http://127.0.0.1:1234
Running 20s test @ http://127.0.0.1:1234
  1 threads and 20 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.54ms  326.87us  13.08ms   96.50%
    Req/Sec    12.86k   838.71    14.12k    78.50%
  256005 requests in 20.02s, 15.28GB read
Requests/sec:  12790.42
Transfer/sec:    781.85MB
```

without cache
```
> sudo sh -c "sync && echo 3 > /proc/sys/vm/drop_caches"

> ./wrk -c 20 -t 1 -d 20 -s get_cfs1.lua http://127.0.0.1:1234
Running 20s test @ http://127.0.0.1:1234
  1 threads and 20 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    90.26ms   64.02ms 351.87ms   78.88%
    Req/Sec   252.98    149.41   660.00     65.61%
  4833 requests in 20.02s, 295.43MB read
Requests/sec:    241.37
Transfer/sec:     14.75MB
```
It's strange that iostop shows the read speed has reached more than 35MB/s but the transfer speed here is only 15MB/s.

```
> strace -c -w -p 26810
strace: Process 26810 attached
^Cstrace: Process 26810 detached
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 77.24   16.083439        1653      9725           read
 15.18    3.160417        6320       500           epoll_wait
  3.37    0.701037         144      4867           write
  2.77    0.576909          59      9744           epoll_ctl
  1.43    0.297166          61      4852           lseek
  0.01    0.001863          44        42           fcntl
  0.01    0.001702         113        15           stat
  0.00    0.000919          43        21           accept
  0.00    0.000330          15        21           close
------ ----------- ----------- --------- --------- ----------------
100.00   20.823781                 29787           total
```

2. read files sequentially

get_cfs2.lua
```
counter = 1

request = function()
   path = "/test_" .. counter
   counter = counter + 1
   return wrk.format(nil, path)
end
```

```
> sudo sh -c "sync && echo 3 > /proc/sys/vm/drop_caches"
> ./wrk -c 20 -t 1 -d 20 -s get_cfs2.lua http://127.0.0.1:1234
Running 20s test @ http://127.0.0.1:1234
  1 threads and 20 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    33.55ms   14.77ms 201.97ms   53.97%
    Req/Sec   600.39    144.40     0.92k    53.50%
  11959 requests in 20.01s, 731.02MB read
Requests/sec:    597.51
Transfer/sec:     36.52MB
```

```
> strace -c -w -p 26810
strace: Process 26810 attached
^Cstrace: Process 26810 detached
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 64.99   11.623380         482     24085           read
 16.23    2.903277        2381      1219           epoll_wait
  7.52    1.344647          55     24105           epoll_ctl
  7.39    1.321203         109     12032           write
  3.85    0.688682          57     12032           lseek
  0.01    0.002199          52        42           fcntl
  0.01    0.001156          55        21           accept
  0.00    0.000325          15        21           close
------ ----------- ----------- --------- --------- ----------------
100.00   17.884870                 73557           total
```

Why reading randomly is screamingly slow?

* ❌ it takes more time to seek to a random location
* ❌ calling `math.random` in generating the request take a considerable amount of time
* ✅ the strace profiling results show it differs in the speed of read syscall. This can be explained by the pre-reading. When we read 64KB of data, the system may read more than that and it may not need to access the disk again in the next read.

3. always read the same file (using cache)

```
> ./wrk -c 20 -t 1 -d 20 http://127.0.0.1:1234/test_456

Running 20s test @ http://127.0.0.1:1234/test_456
  1 threads and 20 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.32ms  236.77us   7.73ms   95.38%
    Req/Sec    15.06k     0.85k   16.45k    78.00%
  299619 requests in 20.00s, 17.89GB read
Requests/sec:  14979.74
Transfer/sec:      0.89GB
```

