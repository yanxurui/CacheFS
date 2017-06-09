local redis = require "resty.redis"
local config = require "config"

local _M = {}

local function init()
    local red = redis:new()
    local ok, err = red:connect(config.redis_ip, config.redis_port)
    if not ok then
        ngx.log(ngx.ERR, "failed to connect redis: ", err)
        return
    end
    return red
end

local function keepalive(red)
    local ok, err = red:set_keepalive(10000, 100)
    if not ok then
        ngx.log(ngx.ERR, "failed to set keepalive: ", err)
        return
    end
end


function _M.set(key, value)
    local red = init()
    if not red then
        return 500
    end
    local ok, err = red:set(key, value)

    keepalive(red)

    if not ok then
        ngx.log(ngx.ERR, "failed to set ", key, ": ", err)
        return 500
    end

    return 200
end

function _M.get(key)
    local red = init()
    if not red then
        return 500
    end
    local res, err = red:get(key)

    keepalive(red)

    if not res then
        ngx.log(ngx.ERR, "failed to get ", key)
        return 500
    end

    if res == ngx.null then
        return 404
    end
    return 200, res
end

function _M.del(key)
    local red = init()
    if not red then
        return 500
    end
    local ok, err = red:del(key)
    if not ok then
        ngx.log(ngx.ERR, "failed to delete ", key, ": ", err)
        return 500
    elseif ok == 0 then
        ngx.log(ngx.WARN, "failed to delete ", key, ': not found')
        return 404
    else
        return 200
    end
end

return _M