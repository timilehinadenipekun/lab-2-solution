from sys import argv
import socket

def help():
    print("httpclient.py [GET/POST] [URL] [key1] [value1] [key2] [value2] ...\n")

class HTTPResponse:
    def __init__(self, code=200, body=""):
        self.code = code
        self.body = body

class HTTPClient:
    
    def connect(self, host, port):
        return None   

    def get_code(self, data):
        return None

    def get_headers(self,data):
        return None

    def get_body(self, data):
        return None
    

    def sendall(self, data):
        self.socket.sendall(data.encode('utf-8'))
        
    def close(self):
        self.socket.close()

    
    # Receive the response
    def read_response(self):
        response = b""
        return response


    def GET(self, url, args=None):
         return HTTPResponse(code, body)

    def POST(self, url, args=None):
        return HTTPResponse(code, body)
    
    def command(self, command, url, args):
        assert isinstance(url, str)
        assert isinstance(args, dict)
        if command == "POST":
            return  self.POST(url, args)
        elif command == "GET":
            return  self.GET(url, args)
        else:
            raise ValueError("not get or post")
    


if __name__ == "__main__":
    client = HTTPClient()
    if len(argv) < 3:
        help()
    else:
        method = argv[1]
        url = argv[2]
    key = None
    args = dict()
    for arg in argv[3:]:
        if key is None:
            key = arg
        else:
            args[key] = arg
            key = None
    if key is not None:
        args[key] = ""
    result = client.command(method, url, args)