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
        if ":" in host:
            family = socket.AF_INET6
        else:
            family = socket.AF_INET

        self.socket = socket.socket(family, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        print(f"connected to server at host {host} and port {port}")

    def parse_url(self, url):
        if not url.startswith("http://"):
            raise ValueError("URL must start with http://")
        url = url.removeprefix("http://")
        parts = url.split("/", 1)
        server_part = parts[0]
        if len(parts) > 1:
            path = "/" + parts[1]
        else:
            path = "/"
        if server_part.startswith("["):
             end = server_part.find("]")
             host = server_part[1:end]
             if ":" in server_part[end+1:]:
                 port = int(server_part[end+2:])
             else:
                 port = 80
        elif ":" in server_part:
            host, port = server_part.split(":", 1)
            port = int(port)
        else:
            host = server_part
            port = 80
                 
        return host, port, path
    
    def percent_encode(self, text: str) -> str:
        safe_chars = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-~")
        encoded = []
        for byte in text.encode("utf-8"):
            if byte in safe_chars:
                encoded.append(chr(byte))
            else:
              encoded.append(f"%{byte:02X}")
        return "".join(encoded)

    def percent_encode_path(self, text: str) -> str:
        safe_chars = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-~/")
        encoded = []
        for byte in text.encode("utf-8"):
            if byte in safe_chars:
                encoded.append(chr(byte))
            else:
                encoded.append(f"%{byte:02X}")
        return "".join(encoded)

    def get_code(self, data):
        status_line = data.split(b"\r\n", 1)[0]
        parts = status_line.decode("utf-8").split(" ")
        return int(parts[1])

    def get_headers(self, data):
        # Split headers from body and decode safely
        header_text = data.split(b"\r\n\r\n", 1)[0].decode("utf-8", errors="ignore")
        headers = {}
        for line in header_text.split("\r\n")[1:]:
        # Only parse lines that actually contain a colon
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()
        return headers

    def get_body(self, data):
        parts = data.split(b"\r\n\r\n", 1)

        if len(parts) <= 1:
            return ""

        body = parts[1]
        headers = self.get_headers(data)

        content_type = headers.get("Content-Type", "").lower()

        if "iso-8859-1" in content_type:
            return body.decode("iso-8859-1")

        return body.decode("utf-8")

    def sendall(self, data):
        self.socket.sendall(data.encode('utf-8'))
        
    def close(self):
        self.socket.close()

    
# Receive the response
    def read_response(self):
        response = b""
        with self.socket.makefile('rb') as sock_file:
            response = sock_file.read()
        return response


    def GET(self, url, args=None):
        host, port, path = self.parse_url(url)
        path = self.percent_encode_path(path)
        if args:
            query = []
            for key in args:
                value = args[key]
                query.append(
                    f"{self.percent_encode(str(key))}={self.percent_encode(str(value))}"
                )
            path = path + "?" + "&".join(query)
        if ":" in host:
            host_header = f"[{host}]"
        else:
            host_header = host
    
        if port != 80:
            host_header = f"{host_header}:{port}"

        request = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host_header}\r\n"
                f"Connection: close\r\n"
                f"\r\n"
         )
       
        self.connect(host, port)
        self.sendall(request)
        response = self.read_response()
        code = self.get_code(response)
        body = self.get_body(response)
        self.close()
        return HTTPResponse(code, body)

    def POST(self, url, args=None):
        host, port, path = self.parse_url(url)
        path = self.percent_encode_path(path)

        # Turn args into the POST body
        body_parts = []

        if args:
            for key in args:
                value = args[key]
                body_parts.append(
                    f"{self.percent_encode(str(key))}={self.percent_encode(str(value))}"
                )

        post_body = "&".join(body_parts)

        if ":" in host:
            host_header = f"[{host}]"
        else:
            host_header = host

        if port != 80:
            host_header = f"{host_header}:{port}"

        request = (
            f"POST {path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            f"Content-Type: application/x-www-form-urlencoded\r\n"
            f"Content-Length: {len(post_body.encode('utf-8'))}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
            f"{post_body}"
            )

        self.connect(host, port)
        self.sendall(request)

        response = self.read_response()

        code = self.get_code(response)
        body = self.get_body(response)

    
        self.close()

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