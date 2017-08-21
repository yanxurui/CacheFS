mount_point = '/data/cache2/yxr'
volume_size = 1024*1024*1024 # 1G
volume_num = 10

log_level = 'WARNING'
log_file = 'cfs.log'
log_slow = 0.1 # 100ms

ip = '0.0.0.0'
port = 1234

memc_on = False
memc_ip = '127.0.0.1'
memc_port = 11211
# a file is cached in memcache only if it's missed 3 times in the past 1 minute
cache_after_miss_count = 3
cache_after_miss_count_duration = 60 # s
