require 'util'
local config = require 'config'
local redish = require 'redis_helper'

local log = ngx.log
local ERR = ngx.ERR

local _M = {}


local write_point = nil
-- write_point = {f, volume_id, write_offset, erase_offset}
local fset={}
-- fset = {
--  volume_id1 = file1,
--  volume_id2 = file2,
--  ...
-- }
local volume_num = math.floor(config.max_capacity/config.volume_size)

local function compute_length(key_len, data_len)
    return #tostring(key_len) + key_len + #tostring(data_len) + data_len + 2
end

local function get_file(volume_id)
    local f = fset[volume_id]
    if not f then
        local path = config.mount_point..'/'..volume_id
        f = io.open(path, 'rb')
        if not f then
            log(ERR, "failed to open file: ", path)
            -- todo
            return
        end
        fset[volume_id] = f
    end
    return f
end

function _M.read(key)
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
        log(ERR, 'failed to seek: ', err)
        return 500
    end
    -- todo opt: read once
    local key_len = f:read("*n")
    f:seek("cur", 1)
    assertEqual(key_len, #key)
    assertEqual(f:read(key_len), key)
    local data_len = f:read("*n")
    assertEqual(compute_length(key_len, data_len), size)
    f:seek("cur", 1)
    local data = f:read(data_len)
    if not data then
        return 500, 'maybe reach end of file'
    end
    return 200, data
end

local function erase(len)
    local write_offset = write_point.write_offset
    local erase_offset = write_point.erase_offset
    log(ngx.INFO, 'write_offset:', write_offset, ',erase_offset:', erase_offset, ',len:', len)
    -- write to a new file
    if erase_offset < write_offset then
        return {}
    end
    -- todo: use a specific file object for this
    local ef = get_file(write_point.volume_id)
    local ok, err = ef:seek("set", erase_offset)
    if not ok then
        log(ERR, "failed to seek: ", err)
        return false, err
    end
    erased_keys = {}
    -- stop loop when there is enough room for new file
    -- or there is no file to erase
    while erase_offset-write_offset<len and erase_offset < config.volume_size do
        assertEqual(ef:seek(), erase_offset)
        local key_len = ef:read("*n")
        if not key_len then
            log(ngx.WARN, "failed to erase, maybe reach end of file")
            break
        end
        ef:seek("cur", 1)
        local key = ef:read(key_len)
        table.insert(erased_keys, key)
        log(ngx.INFO, key, ' was erased')
        local data_len = ef:read("*n")
        ef:seek("cur", data_len+1)
        erase_offset = erase_offset + compute_length(key_len, data_len)
    end
    write_point.erase_offset = erase_offset
    return erased_keys
end

local function update_write_point()
    local volume_id, write_offset
    if not write_point then
        -- restore from redis
        local code, res = redish.get(config.mount_point)
        if code == 200 then
            local temp = split(res, ',')
            volume_id, write_offset, erase_offset = tonumber(temp[1]), tonumber(temp[2]), tonumber(temp[3])
        elseif code == 404 then
            log(ngx.WARN, 'restore write point not found in redis')
            volume_id, write_offset, erase_offset = 0, 0, 0
        else
            log(ERR, 'failed to restore write point from redis: ', res)
            return
        end
    else
        -- if the size of the current file is bigger than limit
        -- then open another file to write
        if write_point.write_offset >= config.volume_size then
            volume_id = (write_point.volume_id+1)%volume_num
            log(ngx.INFO, 'rotate to volume ', volume_id)
            write_point.f:close()
            write_offset, erase_offset = 0, 0
        else
            return
        end
    end

    -- save in module
    write_point = {
        volume_id = volume_id,
        write_offset = write_offset,
        erase_offset = erase_offset
    }

    -- open file
    local path = config.mount_point..'/'..volume_id
    -- update mode, all previous data is preserved, in binary mode
    local f = io.open(path, 'rb+')
    if not f then
        -- maybe not exist
        f = io.open(path, 'wb')
        if not f then
            log(ERR, "failed to open file: ", path)
            return
        end
    end
    local pos, err = f:seek("set", write_offset)
    if not pos then
        log(ERR, 'failed to seek: ', err)
        return
    end

    write_point.f = f
end

function _M.write(key, data)
    -- write to file
    update_write_point()
    local key_len = #key
    local data_len = #data
    local length = compute_length(key_len, data_len)
    -- make room for write
    local erased_keys, err = erase(length)
    if not erased_keys then
        return 500, err
    end
    local ok, err = write_point.f:write(key_len, ':', key, data_len, ':', data)
    if not ok then
        log(ERR, 'failed to write: ', err)
        return 500
    end
    -- enable read immediately
    write_point.f:flush()

    -- save index
    -- update write_offset
    local write_offset=write_point.write_offset
    write_point.write_offset = write_offset+length
    -- todo
    local status, res
    for i, k in ipairs(erased_keys) do
        status, res = redish.del(k)
        if status == 500 then
            log(ngx.INFO, 'failed to erase ', k)
        end
    end
    local status, res = redish.set(key, table.concat({write_point.volume_id, write_offset, length}, ','))
    if status ~= 200 then
        return status, res
    end
    return redish.set(config.mount_point, table.concat({write_point.volume_id, write_point.write_offset, write_point.erase_offset}, ','))
end

function _M.delete(key)
    -- delete index
    return redish.del(key)
end


return _M



