mount_point = '/tmp/CacheFS'
volume_size = 1*1024*1024 # 1 MB
volume_num = 2

log_level = 'DEBUG'
log_file = 'tests/cfs.log'
log_slow = 0.1

ip = '127.0.0.1'
port = 1235

memc_on = True
memc_ip = '127.0.0.1'
memc_port = 11211
cache_after_miss_count = 2
cache_after_miss_count_duration = 0.5
