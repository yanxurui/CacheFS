local fs = require 'fs'

local key = string.sub(ngx.var.uri, 2)
if key == '' then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.say('no key specified')
    return ngx.exit(ngx.OK)
end
key = ngx.escape_uri(key)

local method = ngx.req.get_method()

local status, res
if method == 'GET' then
    status, res = fs.read(key)
    if status == 200 then
        ngx.print(res)
        return ngx.exit(ngx.OK)
    end
elseif method == 'PUT' then
    local data = ngx.req.get_body_data()
    if not data then
        status = ngx.HTTP_BAD_REQUEST
        res = 'body is empty'
    else
        status, res = fs.write(key, data)
    end
elseif method == 'DELETE' then
    status, res = fs.delete(key)
else
    status = HTTP_METHOD_NOT_IMPLEMENTED
end

if status then
    ngx.status = status
end
if res then
    ngx.say(res)
end
ngx.exit(ngx.OK)

