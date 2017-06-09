local _M = {
    mount_point = '/data/cache2/yxr',
    max_capacity = 2*1024*1024,
    volume_size = 1024*1024,

    redis_ip = '127.0.0.1',
    redis_port = 6379,

    sync_every = 3 -- seconds
}

return _M
