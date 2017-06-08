require 'util'
local config = require 'config'
local redish = require 'redis_helper'


local _M = {}


local write_point = nil
-- write_point = {f, volume_id, offset, erase_offset}
local fset={}
-- fset = {
--  volume_id1 = f1,
--  volume_id2 = f2,
--  ...
-- }
local volume_num = math.floor(config.max_capacity/config.volume_size)


local function update_write_point()
    local volume_id, offset
    if not write_point then
        local code, res = redish.get(config.mount_point)
        if code == 200 then
            local temp = split(res, ',')
            volume_id, offset = tonumber(temp[1]), tonumber(temp[2])
        elseif code == 404 then
            ngx.log(ngx.WARN, 'restore write point not found in redis')
            volume_id, offset = 0, 0
        else
            ngx.log(ngx.ERR, 'failed to restore write point from redis: ', res)
            return
        end
    else
        -- if the size of the current file is bigger than limit
        -- then open another file to write
        if write_point.offset > config.volume_size then
            volume_id = (write_point.volume_id+1)%volume_num
            ngx.log(ngx.INFO, 'rotate to volume ', volume_id)
            write_point.f:close()
            offset = 0
        else
            return
        end
    end

    -- save in module
    write_point = {
        volume_id = volume_id,
        offset = offset
    }

    -- open file
    local path = config.mount_point..'/'..volume_id
    -- update mode, all previous data is preserved, in binary mode
    local f = io.open(path, 'rb+')
    if not f then
        -- maybe not exist
        f = io.open(path, 'wb')
        if not f then
            ngx.log(ngx.ERR, "failed to open file: ", path)
            return
        end
    end
    local pos, err = f:seek("set", offset)
    if not pos then
        ngx.log(ngx.ERR, 'failed to seek: ', err)
        return
    end

    write_point.f = f
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
    update_write_point()
    -- write to file
    local ok, err = write_point.f:write(data)
    if not ok then
        ngx.log(ngx.ERR, 'failed to write: ', err)
        return 500
    end
    -- https://stackoverflow.com/questions/7127075/what-exactly-the-pythons-file-flush-is-doing
    -- write out any data that lingers in a program buffer to the actual file. 
    -- Specifically what this means is that if another process has that same file open for reading, 
    -- it will be able to access the data you just flushed to the file. However, it does not necessarily mean it has been "permanently" stored on disk.
    write_point.f:flush()

    local length = #data
    -- update offset
    local offset=write_point.offset
    write_point.offset = offset+length
    -- save index
    -- todo
    local status, res = redish.set(key, table.concat({write_point.volume_id, offset, length}, ','))
    if status ~= 200 then
        return status, res
    end
    return redish.set(config.mount_point, table.concat({write_point.volume_id, write_point.offset}, ','))
end

local function get_file(volume_id)
    local f = fset[volume_id]
    if not f then
        local path = config.mount_point..'/'..volume_id
        f = io.open(path, 'rb')
        if not f then
            ngx.log(ngx.ERR, "failed to open file: ", path)
            -- todo
            return
        end
        fset[volume_id] = f
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


return _M



