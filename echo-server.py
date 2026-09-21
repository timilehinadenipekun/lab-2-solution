#!/usr/bin/env python3

"""
CMPUT 404 Echo Server
=====================

A local stand-in for the buttercup echo server.

It answers every GET/POST with an HTML page describing *exactly* what it
received: the raw request line, the raw (still percent-encoded) path and body,
the decoded query parameters, and the decoded form fields. That makes it easy to
see whether your client is percent-encoding, building query strings, and
sending POST bodies correctly.

Run it:

    python3 echo-server.py            # http://localhost:9000/
    python3 echo-server.py 9001       # a different port
    python3 echo-server.py 9000 ::1   # listen on IPv6 loopback

Then point your client at it:

    python3 httpclient.py GET  http://localhost:9000/ name value
    python3 httpclient.py POST http://localhost:9000/ name value

Special paths:

    /redirect/301/   ->  301 Moved Permanently (also 302, 307, 308)
    /status/404/     ->  responds with that status code
    anything else    ->  200 OK with the echo page

NOTE: This file is part of the test harness, NOT part of your submission.
The import restrictions in the assignment apply to httpclient.py and server.py.
Do not modify this file.
"""

import html
import http.server
import json
import re
import socket
import sys
from urllib.parse import parse_qsl, urlsplit

SERVER_NAME = "CMPUT404EchoServer/1.0"
REDIRECT_RE = re.compile(r"^/redirect/(\d{3})/?$")
STATUS_RE = re.compile(r"^/status/(\d{3})/?$")


def page(title, sections):
    """Build the HTML echo page. `sections` is a list of (heading, html) pairs."""
    body = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        f"<title>{html.escape(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{html.escape(title)}</h1>",
    ]
    for heading, content in sections:
        body.append(f"<h2>{html.escape(heading)}</h2>")
        body.append(content)
    body.append("</body>")
    body.append("</html>")
    return "\n".join(body) + "\n"


def pre(text):
    return "<pre>" + html.escape(text) + "</pre>"


def as_json(obj):
    # ensure_ascii=False so emoji and other non-ASCII characters show up as
    # themselves instead of \uXXXX escapes.
    return pre(json.dumps(obj, indent=2, ensure_ascii=False))


def as_fields(pairs):
    if not pairs:
        return "<p>(none)</p>"
    items = [
        f"<li><code>{html.escape(k)}</code> = <code>{html.escape(v)}</code></li>"
        for k, v in pairs
    ]
    return "<ul>\n" + "\n".join(items) + "\n</ul>"


class EchoHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = SERVER_NAME
    sys_version = ""

    def log_message(self, fmt, *args):
        sys.stderr.write("echo-server: %s\n" % (fmt % args))

    def respond(self, status, body, extra_headers=()):
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        for key, value in extra_headers:
            self.send_header(key, value)
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)
        self.close_connection = True

    def read_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        if length <= 0:
            return ""
        return self.rfile.read(length).decode("utf-8", "replace")

    def echo(self, raw_body=""):
        parts = urlsplit(self.path)
        query_pairs = parse_qsl(parts.query, keep_blank_values=True)
        form_pairs = parse_qsl(raw_body, keep_blank_values=True)
        headers = {k.lower(): v for k, v in self.headers.items()}

        sections = [
            ("Request line", pre(self.requestline)),
            ("Method", pre(self.command)),
            ("Raw path (exactly as you sent it)", pre(parts.path)),
            ("Raw query string (exactly as you sent it)", pre(parts.query)),
            ("Decoded query parameters", as_json(dict(query_pairs))),
            ("Raw body (exactly as you sent it)", pre(raw_body)),
            ("Decoded form fields", as_fields(form_pairs)),
            ("Headers", as_json(headers)),
        ]
        self.respond(200, page("CMPUT 404 Echo Server", sections))

    def special(self):
        """Handle /redirect/NNN/ and /status/NNN/. Returns True if handled."""
        path = urlsplit(self.path).path

        match = REDIRECT_RE.match(path)
        if match:
            code = int(match.group(1))
            body = page(
                f"{code} Redirect",
                [("Location", pre("/"))],
            )
            self.respond(code, body, extra_headers=[("Location", "/")])
            return True

        match = STATUS_RE.match(path)
        if match:
            code = int(match.group(1))
            self.respond(code, page(f"{code}", [("Requested status", pre(str(code)))]))
            return True

        return False

    def do_GET(self):
        if not self.special():
            self.echo()

    def do_POST(self):
        body = self.read_body()
        if not self.special():
            self.echo(raw_body=body)

    def do_HEAD(self):
        self.respond(200, "")

    def handle_other(self):
        self.respond(405, page("405 Method Not Allowed", []))

    do_PUT = do_DELETE = do_PATCH = handle_other


class IPv4Server(http.server.ThreadingHTTPServer):
    address_family = socket.AF_INET
    allow_reuse_address = True
    daemon_threads = True


class IPv6Server(IPv4Server):
    address_family = socket.AF_INET6


def serve(host="127.0.0.1", port=9000):
    server_class = IPv6Server if ":" in host else IPv4Server
    with server_class((host, port), EchoHandler) as httpd:
        shown = f"[{host}]" if ":" in host else host
        print(f"Echo server listening on http://{shown}:{port}/", file=sys.stderr)
        print("Press Ctrl+C to stop.", file=sys.stderr)
        httpd.serve_forever()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    try:
        serve(host, port)
    except KeyboardInterrupt:
        print("Echo server stopped.", file=sys.stderr)


if __name__ == "__main__":
    main()
