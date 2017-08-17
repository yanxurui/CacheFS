STATUS = {
    200: '200 OK',
    400: '400 Bad Request',
    404: '404 Not Found',
    500: '500 Internal Server Error',
    501: '501 Not Implemented',
}

class Response:
    def __init__(self, status=200, body='', headers={}):
        self.status = status
        self.body = body
        self.headers = headers

    def get_status(self):
        return STATUS[self.status]

    def get_headers(self):
        headers = []
        for k, v in self.headers.items():
            headers.append((k, str(v)))
        if 'Content-Length' not in self.headers:
            headers.append(('Content-Length', str(len(self.body))))
        return headers
