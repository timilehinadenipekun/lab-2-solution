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

class LabServer(socketserver.TCPServer):
    allow_reuse_address = True

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
        start_line = self.recieve_line()
        print("<", start_line)

def main():
    # From https://docs.python.org/3/library/socketserver.html, The Python Software Foundation, downloaded 2024-01-07
    with LabServer((HOST, PORT), LabServerTCPHandler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()