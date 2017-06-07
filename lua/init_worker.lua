local config = require 'config'
local fs = require 'fs'

local delay = config.sync_every
local new_timer = ngx.timer.at
local log = ngx.log
local ERR = ngx.ERR

local flush
flush = function(premature)
    if not premature then
        log(ngx.INFO, 'flush every ', delay, ' seconds')
        fs.flush()
        local ok, err = new_timer(delay, flush)
        if not ok then
            log(ERR, "failed to create timer: ", err)
            return
        end
    end
end

local ok, err = new_timer(delay, flush)
if not ok then
    log(ERR, "failed to create timer: ", err)
    return
end
