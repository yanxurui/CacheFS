require 'util'
local config = require 'config'
local redish = require 'redis_helper'

local _M = {
    volume_num = math.floor(config.max_capacity/config.volume_size),
    -- write_point = {f, volume_id, offset}
    fset={}
    -- fset = {
    --  volume_id1 = f1,
    --  volume_id2 = f2,
    --  ...
    -- }
}
local function update_write_point(volume_id, offset)
    -- save in module
    _M.write_point = {
        ['volume_id'] = volume_id,
        ['offset'] = offset
    }

    -- open file
    local path = config.mount_point..'/'..volume_id
    local f = io.open(path, 'wb') -- write mode, in binary mode 
    if not f then
        ngx.log(ngx.ERR, "failed to open file: ", path)
        -- todo
        return
    end
    local pos, err = f:seek("set", offset)
    if not pos then
        ngx.log(ngx.ERR, 'failed to seek: ', err)
        return
    end

    _M.write_point['f'] = f

end
local function get_write_point()
    local volume_id, offset
    if not _M.write_point then
        local code, res = redish.get(config.mount_point)
        if code == 200 then
            local write_point = split(res, ',')
            volume_id, offset = tonumber(write_point[1]), tonumber(write_point[2])
        elseif code == 404 then
            ngx.log(ngx.WARN, 'restore write point not found in redis')
            volume_id, offset = 0, 0
        else
            ngx.log(ngx.ERR, 'failed to restore write point from redis: ', res)
            return
        end
        update_write_point(volume_id, offset)
    else
        local old_volume_id = _M.write_point['volume_id']
        -- if the size of the current file is bigger than limit
        -- then open another file for write
        if _M.write_point['offset'] > config.volume_size then
            volume_id = (old_volume_id+1)%volume_num
            if volume_id ~= old_volume_id then
                ngx.log(ngx.INFO, 'rotate to volume ', volume_id)
            end
            _M.write_point['volume_id'] = volume_id
            _M.write_point['offset'] = 0
            offset = 0
            _M.write_point['f']:close()
            update_write_point(volume_id, offset)
        end
    end

    return _M.write_point
end

function _M.write(key, data)
    -- set to cache
    local cache = ngx.shared.cache
    local succ, err, forcible = cache:set(key, data, config.sync_every+1)
    if not succ then
        ngx.log(ngx.ERR, "failed to set to shared dict: ", err)
        return 500
    elseif forcible then
        ngx.log(ngx.WARN, key, " is set forciblely")
    end

    -- get write point
    local write_point = get_write_point()
    local volume_id=write_point['volume_id']
    local offset=write_point['offset']
    local f=write_point['f']
    -- write to file
    local f, err = f:write(data)
    if not f then
        ngx.log(ngx.ERR, 'failed to write: ', err)
        return 500
    end
    local length = #data
    -- update write point
    write_point['offset'] = offset+length
    -- save index
    -- todo

    local status, res = redish.set(key, table.concat({volume_id, offset, length}, ','))
    if status ~= 200 then
        return status, res
    end
    return redish.set(config.mount_point, table.concat({volume_id, write_point['offset']}, ','))
end

local function get_file(volume_id)
    local f = _M.fset[volume_id]
    if not f then
        local path = config.mount_point..'/'..volume_id
        f = io.open(path, 'rb')
        if not f then
            ngx.log(ngx.ERR, "failed to open file: ", path)
            -- todo
            return
        end
        _M.fset[volume_id] = f
    end
    return f
end

function _M.read(key)
    -- read from cache first
    local cache = ngx.shared.cache
    local value, err = cache:get(key)
    if value then
        return 200, value
    elseif err then
        ngx.log(ngx.ERR, "failed to read from shared dict ", err)
    end

    -- read index
    local status, res = redish.get(key)
    if status ~= 200 then
        return status, res
    end
    local meta = split(res, ',')
    local volume_id = tonumber(meta[1])
    local offset = tonumber(meta[2])
    local size = tonumber(meta[3])
    -- read from disk
    local f = get_file(volume_id)
    local pos, err = f:seek("set", offset)
    if not pos then
        ngx.log(ngx.ERR, 'failed to seek: ', err)
        return 500
    end
    local data = f:read(size)
    if not data then
        return 500, 'maybe reach end of file'
    end
    return 200, data
end

function _M.delete(key)
    -- delete cache
    local cache = ngx.shared.cache
    cache:delete(key)
    -- delete index
    return redish:del(key)
end

-- cannot read from file immediately after write without flush
function _M.flush()
    if _M.write_point then
        _M.write_point['f']:flush()
    end
end

return _M



