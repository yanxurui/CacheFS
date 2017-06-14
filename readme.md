## benchmark

### write

**set a file with size of 200KB**

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


