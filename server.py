#!/usr/bin/env python3

"""
A basic Python 3 HTTP/1.1 server.
"""

import socketserver
import pathlib

HOST = "0.0.0.0"
PORT = 8000
BUFSIZE = 4096
LINE_ENDING='\r\n'
SERVE_PATH = pathlib.Path('www').resolve()
HTTP_1_1 = 'HTTP/1.1'

#Custom server class
class LabServer(socketserver.TCPServer):
    allow_reuse_address = True

#Custom http handler class
class LabServerTCPHandler(socketserver.StreamRequestHandler):
    def __init__(self, *args, **kwargs):
        self.charset = "UTF-8"
        self.serve_path = pathlib.Path("www").resolve()
        super().__init__(*args, **kwargs)

    def recieve_line(self):
        return self.rfile.readline().strip().decode(self.charset, 'ignore')
    
    def send_line(self, line):
        self.wfile.write((line + LINE_ENDING).encode(self.charset, 'ignore'))
    
    def handle(self):
        request_line = self.rfile.readline().strip().decode('utf-8')
        print("<", request_line)
        method, path, _ = request_line.split(' ', 2)
        headers = self.parse_headers()
        if method == 'GET':
            path = self.percent_decode(path)
            file_path = (self.serve_path / path.lstrip("/")).resolve()
            if file_path.is_dir():
                if not path.endswith("/"):
                    self.send_line("HTTP/1.1 301 Moved Permanently")
                    self.send_line(f"Location: {path}/")
                    self.send_line("Content-Length: 0")
                    self.send_line("Connection: close")
                    self.send_line("")
                    return

                file_path = file_path / "index.html"
            if not file_path.exists():
                self.send_line("HTTP/1.1 404 Not Found")
                self.send_line("Content-Length: 0")
                self.send_line("Connection: close")
                self.send_line("")
                return

            body = file_path.read_bytes()

            if file_path.suffix == ".css":
                content_type = "text/css"
            else:
                content_type = "text/html"

            self.send_line("HTTP/1.1 200 OK")
            self.send_line(f"Content-Type: {content_type}")
            self.send_line(f"Content-Length: {len(body)}")
            self.send_line("Connection: close")
            self.send_line("")
            self.wfile.write(body)
        else:
            self.send_line("HTTP/1.1 405 Method Not Allowed")
            self.send_line("Allow: GET")
            self.send_line("")
            return

    def parse_headers(self):
       headers = {}
       while True:
           line = self.rfile.readline().strip().decode('utf-8')
           if not line:
               break
           key, value = line.split(":", 1)
           headers[key.strip()] = value.strip()
       return headers
    
    def percent_decode(self, text):
        decoded = bytearray()
        i = 0

        while i < len(text):
            if text[i] == "%" and i + 2 < len(text):
                decoded.append(int(text[i + 1:i + 3], 16))
                i += 3
            else:
                decoded.extend(text[i].encode("utf-8"))
                i += 1

        return decoded.decode("utf-8")

def main():
    # From https://docs.python.org/3/library/socketserver.html, The Python Software Foundation, downloaded 2024-01-07
    with LabServer((HOST, PORT), LabServerTCPHandler) as server:
        print("server is starting")
        print("running")
        server.serve_forever()


if __name__ == "__main__":
    main()