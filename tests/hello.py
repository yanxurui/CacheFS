# test the best performance of bjoern

def app(env, start_response):
    body = "hello world"
    start_response(
        '200 OK',
        [('Content-type', 'text/plain'), ('Content-Length', str(len(body)))]
        # [('Content-type', 'text/plain')]
    )
    return [body]

import bjoern

bjoern.run(
    wsgi_app=app,
    host='0.0.0.0',
    port=1235
)
