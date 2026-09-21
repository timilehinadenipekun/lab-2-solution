import sys
import subprocess
from typing import Any
from multiprocessing import Process
import pathlib
import re
import traceback
import random
import difflib
from urllib import request
from urllib.parse import urljoin, urlsplit
import http
import http.server
from http import HTTPStatus
from inspect import cleandoc
import os
import json
import time
import socket

MAX_SAFE_INT = 2**53-1

class NoErrorHTTPErrorProcessor(request.HTTPErrorProcessor):
    def http_response(self, request, response):
        return response
class NoRedirectHTTPRedirectHandler(request.HTTPRedirectHandler):
    def http_response(self, request, response):
        return response
request.install_opener(request.build_opener(
    NoErrorHTTPErrorProcessor,
    NoRedirectHTTPRedirectHandler
))

NAME = pathlib.Path(__file__).name

class TestEntry:
    def __init__(self, tester, print_args) -> None:
        self.tester = tester
        self.print_args = print_args
        self.entered = False

    def __enter__(self):
        self.tester.enter(*self.print_args)
        self.entered = True
    
    def __exit__(self, exc_type, exc_value, _traceback):
        if (not exc_type) and (not exc_value):
            self.tester.leave()
        self.entered = False

class Tester:
    def __init__(self) -> None:
        self.inside = []
        self.cleanup = []
        self.passed = 0
    
    def number(self):
        return self.passed + len(self.inside)
    
    def print_indented(self, *print_args):
        indent = "..." * len(self.inside)
        print(NAME, indent, *print_args, file=sys.stderr)

    def enter(self, *print_args):
        self.print_indented(f"{self.number():04}", "Checking", *print_args)
        self.inside.append(print_args)
    
    def leave(self):
        print_args = self.inside.pop()
        self.passed += 1
        self.print_indented(f"{self.number():04}", "OK", *print_args)
    
    def run(self, *functions):
        self.failed = False
        for function in functions:
            try:
                function(self)
            except Exception as e:
                tb = traceback.TracebackException.from_exception(e)
                self.failed = True
                print("\n".join(tb.format(chain=False)), file=sys.stderr)
                if isinstance(e, http.client.RemoteDisconnected):
                    self.print("'Remote Disconnected' error is probably the result of an earlier error, scroll up!")
                while len(self.inside) > 0:
                    print_args = self.inside.pop()
                    self.print_indented(f"{self.number():04}", "FAIL", *print_args)
            finally:
                for cleanup_func in self.cleanup:
                    cleanup_func()
            # assert len(self.inside) == 0
            if not self.failed:
                self.print("ALL OK")
                self.print("Remember:")
                self.print("""
                    Your code still needs to follow all the rules and
                    perform its functions as described in the assignment.
                    
                    * This does not test everything possible.
                    * secret_tests will be run to make sure your code
                        isn't "memorizing" answers.
                    * You must NOT include any imports that aren't allowed
                        by the assignment, and follow all the other rules listed
                        in the assignment.
                    
                    Go re-read the assignment.
                """)
    
    def print(self, *args):
        self.print_indented(*args)
    
    def __call__(self, *print_args) -> Any:
        return TestEntry(self, print_args)

RANDOM_NUMBER_PREFIX = "Here's a random number: "
RANDOM_NUMBER_REGEX = re.escape(RANDOM_NUMBER_PREFIX) + r'\d+'

def relate(base, relative=None, *more):
    if relative is None:
        return base
    
    dot = hex(random.randrange(2**128))[2:]
    base = base.replace('.', dot)
    relative = relative.replace('.', dot)
    result = urljoin(base, relative).replace(dot, '.')
    if len(more) > 0:
        return relate(result, *more)
    
    return result

class TestServerHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def make_echo(self):
        self.close_connection = True
        body = dict()
        body['client_address'] = self.client_address
        body['requestline'] = self.requestline
        body['command'] = self.command
        body['server_path'] = self.path
        body['request_version'] = self.request_version
        body['headers'] = dict()
        body['duplicate_headers'] = []
        for key, value in self.headers.items():
            if key in body['headers']:
                body['duplicate_headers'].append([key.lower(), value])
            else:
                body['headers'][key.lower()] = value
        parts = urlsplit(self.path)
        body['path'] = parts.path
        body['query'] = parts.query
        body['fragment'] = parts.fragment
        body['key'] = self.key
        return json.dumps(body, indent=2)

    def do_GET(self):
        print(f"Test server: GET {self.path}")
        if self.path.startswith('/echo'):
            body = self.make_echo()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body.encode('utf-8'))
        else:
            return super().do_GET()

class IPV4Server(http.server.ThreadingHTTPServer):
    address_family = socket.AF_INET
class IPV6Server(http.server.ThreadingHTTPServer):
    address_family = socket.AF_INET6
    def server_bind(self) -> None:
        try:
            self.socket.setsockopt(
                socket.IPPROTO_IPV6,
                socket.IPV6_V6ONLY,
                1
            )
        except:
            pass
        return super().server_bind()

def test_server(addr, port, key):
    print(f"starting test server: {addr!r}, {port!r}", file=sys.stderr)
    os.chdir('www')
    if ':' in addr:
        server_class = IPV6Server
    else:
        server_class = IPV4Server
    TestServerHTTPHandler.key = key
    with server_class((addr, port), TestServerHTTPHandler) as httpd:
        print("Test server at port", port, file=sys.stderr)
        httpd.serve_forever()

index_html = cleandoc("""
    <!DOCTYPE html>
    <html lang="en-CA">
    <head>
        <title>Example Page</title>
        <meta http-equiv="Content-Type" content="text/html;charset=utf-8">
        <!-- check conformance at http://validator.w3.org/check -->
        <link rel="stylesheet" type="text/css" href="base.css">
    </head>
    <body>
        <main class="eg">
            <h1>An Example Page</h1>
            <ul>
                <li>It works?</li>
                <li><a href="deep/index.html">A deeper page</a></li>
                <li>Here's a random number: 6601674</li>
            </ul>
        </main>
    </body>
    </html>
""")

base_css = cleandoc("""
    h1 {
        color:orange;
        text-align:center;
    }
""")

deep_index = cleandoc("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Deeper Example Page</title>
            <meta http-equiv="Content-Type"
            content="text/html;charset=utf-8"/>
            <!-- check conformance at http://validator.w3.org/check -->
            <link rel="stylesheet" type="text/css" href="deep.css">
    </head>

    <body>
        <div class="eg">
            <h1>An Example of a Deeper Page</h1>
            <ul>
                <li>It works?</li>
                            <li><a href="../index.html">A page below!</a></li>
            </ul>
        </div>
    </body>
    </html> 
""")

special_file = cleandoc("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Deeper Example Page</title>
            <meta http-equiv="Content-Type"
            content="text/html;charset=utf-8"/>
            <!-- check conformance at http://validator.w3.org/check -->
            <link rel="stylesheet" type="text/css" href="deep.css">
    </head>

    <body>
        <div class="eg">
            <h1>This is a special page</h1>
            
        </div>
    </body>
    </html> 
""")

deep_css = cleandoc("""
    h1 {
        color:green;
        text-align:center;
    }
""")

ECHO_SERVER_FILE = "echo-server.py"

def start_local_echo_server(tester):
    """Run echo-server.py (our local replacement for buttercup) in another
    process. Returns its base URL, or None if it couldn't be started."""
    path = pathlib.Path(__file__).resolve().parent / ECHO_SERVER_FILE
    if not path.is_file():
        tester.print(f"{ECHO_SERVER_FILE} is missing! Restore it from the starter code.")
        tester.print("Skipping echo tests (percent-encoding, GET/POST args, redirects).")
        time.sleep(2)
        return None

    port = random.randrange(8800, 8899)
    echo_process = subprocess.Popen([sys.executable, str(path), str(port), '127.0.0.1'])

    def cleanup_echo_server():
        tester.print("Killing echo server...")
        echo_process.kill()
        try:
            echo_process.wait(1)
        except subprocess.TimeoutExpired:
            pass
        tester.print("KILLED")
    tester.cleanup.append(cleanup_echo_server)

    for _ in range(50):
        time.sleep(0.1)
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                break
        except OSError:
            continue
    else:
        tester.print("The local echo server didn't start, that shouldn't happen!")
        return None

    tester.print(f"Local echo server running at http://127.0.0.1:{port}/")
    return f"http://127.0.0.1:{port}/"

def one_giant_function(tester):
    global index_html
    with tester("Making www dir..."):
        with tester("you are running this file in the current directory"):
            wd = pathlib.Path(".").resolve()
            me = pathlib.Path(__file__).resolve().parent
            assert wd == me

        www = me / "www"

        if not www.is_dir():
            www.mkdir()

        with tester("writing files"):
            index_html_path = www / "index.html"
            assert RANDOM_NUMBER_PREFIX in index_html
            index_html = re.sub(RANDOM_NUMBER_REGEX, RANDOM_NUMBER_PREFIX+str(random.randrange(9999999)), index_html)
            index_html_path.write_text(index_html)
            assert index_html_path.read_text() == index_html

            base_css_path = www / "base.css"
            base_css_path.write_text(base_css)

            deep_path = www / "deep"
            if not deep_path.is_dir():
                deep_path.mkdir()
            
            deep_index_path = deep_path / "index.html"
            deep_index_path.write_text(deep_index)

            deep_css_path = deep_path / "deep.css"
            deep_css_path.write_text(deep_css)
            special_file_path = deep_path / "special@file.html"
            special_file_path.write_text(special_file)

    tester.enter("your code is named server.py in the same directory as this file!")
    import server
    tester.leave()

    tester.enter("your server has main")
    your_server_main = server.main
    tester.leave()

    tester.enter("your server has PORT")
    your_server_port = server.PORT
    tester.leave()

    tester.enter("starting your server")
    your_server_process = Process(target=your_server_main)
    
    def cleanup_server():
        tester.print("Killing your server...")
        your_server_process.kill()
        your_server_process.join(1)
        tester.print("KILLED")
        assert not your_server_process.is_alive()
    tester.cleanup.append(cleanup_server)

    your_server_process.start()
    tester.leave()

    tester.enter("did your server crash")
    your_server_process.join(1)
    assert your_server_process.is_alive()
    tester.leave()

    base_path = f"http://127.0.0.1:{your_server_port}/"

    def do_urlopen(relatives, data=None, method=None):
        if isinstance(data, str):
            data = data.encode()
        url = relate(base_path, *relatives)
        req = request.Request(url=url, data=data, method=method)
        tester.print(f"{method} {url}")
        return request.urlopen(req, timeout=1)

    def get(*relatives):
        return do_urlopen(relatives, method='GET')
    
    def post(*relatives, data=b''):
        return do_urlopen(relatives, data=data, method='POST')

    def same_text(expected, got):
        def repr_mostly(thing):
            r = repr(thing)
            if r[0] in ['"', "'"] and r[-1] in ['"', "'"]:
                r = r[1:-1]
            return r

        def ws_diff(expected, got):
            expected = list(map(repr_mostly, expected.splitlines(keepends=True)))
            got = list(map(repr_mostly, got.splitlines(keepends=True)))
            return list(difflib.unified_diff(expected, got, fromfile="expected", tofile="recieved"))

        if isinstance(expected, bytes):
            expected = expected.decode()
        if isinstance(got, bytes):
            got = got.decode()
        if expected != got:
            sys.stderr.write(os.linesep.join(ws_diff(expected, got)+['']))
        assert expected == got, "Didn't recieve what I expected, see diff above"
    
    def check_mime(expected, response):
        with tester("Content-Type is accurate"):
            assert 'Content-Type' in response.headers, "Missing Content-Type header"
            got = response.headers['Content-Type']
            if isinstance(expected, bytes):
                expected = expected.decode()
            if isinstance(got, bytes):
                got = got.decode()
            got = got.split(";")[0]
            assert expected == got, "Expected type {expected} got type {got}"

    with tester("get index.html directly"):
        response = get("/index.html")

        with tester("Response 200 OK"):
            assert response.status == 200, f"Expected code 200 got {response.status}"
            assert response.reason == "OK"
        
        with tester("Content is accurate"):
            same_text(index_html, response.read())
        
        check_mime("text/html", response)

    with tester("get /"):
        response = get("")

        with tester("Response 200 OK"):
            assert response.status == 200, f"Expected code 200 got {response.status}"
            assert response.reason == "OK"
        
        with tester("Content is accurate"):
            same_text(index_html, response.read())
        
        check_mime("text/html", response)
    
    with tester("get /base.css"):
        response = get("/base.css")

        with tester("Response 200 OK"):
            assert response.status == 200, f"Expected code 200 got {response.status}"
            assert response.reason == "OK"
        
        with tester("Content is accurate"):
            same_text(base_css, response.read())
        
        check_mime("text/css", response)

    with tester("a page that doesn't exist"):
        dne_path = www / "doesnt_exist.html"
        assert not dne_path.exists()

        with tester("GET /doesnt_exist.html"):
            response = get("doesnt_exist.html")
            assert response.status == 404, f"Expected code 404 got {response.status}"

    with tester("/deep"):
        with tester("GET /deep"):
            response = get("deep")
            assert response.status in [301, 308], f"Expected code 301 got {response.status}"
            assert 'Location' in response.headers, f"Didn't find location header"
            location = response.headers['Location']
            assert location.endswith('/'), location

        with tester("following redirect"):
            response = get(response.url, location)
            assert response.status == 200, f"Expected code 200 got {response.status}"
            same_text(deep_index, response.read())
            check_mime("text/html", response)
            
            with tester("deep/deep.css"):
                response = get(response.url, "deep.css")
            
        with tester(f"GET deep/special@file"):
            encoded_path = 'deep/special%40file.html'
            response = get(encoded_path)
        
            with tester("Response 200 OK"):
                assert response.status == 200, f"Expected code 200 got {response.status}"
                assert response.reason == "OK"
        
            with tester("Content is accurate"):
                same_text(special_file, response.read())

    
    with tester("how secure are you?"):
        response = get("../../../../../../../../../../etc/os-release")
        assert response.status in [403, 404], f"Expected code 403 got {response.status}"
    
    with tester("testing 405s"):
        response = post('', data="heh?")
        assert response.status == 405, f"Expected code 405 got {response.status}"

    
    ######################## CLIENT #####################################
    
    with tester("your client is named httpclient.py in the same directory as this file!"):
        import httpclient
    
    with tester("your client has HTTPClient"):
        client_class = httpclient.HTTPClient
        client = client_class()
    
    with tester("your HTTPClient has command"):
        client.command
    
    mct_url = "http://www.msftconnecttest.com/connecttest.txt"
    try:
        mct = get(mct_url)
        assert mct.status == 200
    except Exception as e:
        tester.print_indented(str(e))
        tester.print_indented("Are you connected to the internet?")
        time.sleep(5)
    else:
        with tester(f"your client can connect to {mct_url}"):
            response = client.command('GET', mct_url, {})
            assert response.code == 200, response.code
            assert "Microsoft Connect Test" == response.body
   
    with tester("your client can connect to your custom server's index.html"):
        response = client.command('GET', f"http://127.0.0.1:{your_server_port}/", {})
        assert response.code == 200, f"Expected code 200 got {response.code}"
        same_text(index_html, response.body)
    with tester("your client can connect to your custom server to get a page that does not exist "):
        response = client.command('GET', f"http://127.0.0.1:{your_server_port}/buffalo.html/", {})
        assert response.code == 404, f"Expected code 404 got {response.code}"


    
    with tester("your client can connect to google.com"):
        response = client.command('GET', 'http://google.com', {})
        assert response.code == 301, response.code
        assert "301 Moved" in response.body

    with tester("your client can connect to www.google.com"):
        response = client.command('GET', 'http://www.google.com', {})
        assert response.code == 200, response.code
        assert "<title>Google" in response.body

    with tester("your client works with 404 errors"):
        response = client.command('GET', 'http://postman-echo.com/status/404', {})
        assert response.code == 404, response.code

    with tester("your client works with 200 ok"):
        response = client.command('GET', 'http://webdocs.cs.ualberta.ca/~hazelcam/', {})
        assert response.code == 200
        assert 'Index of /~hazelcam' in response.body
    
    with tester("your client POSTS to server that doesn't accept post"):
        response = client.command('POST', 'http://webdocs.cs.ualberta.ca/~hazelcam/', {})
        assert response.code >= 400, response.code
        assert response.code < 500, response.code

    with tester("your client POSTS to server that doesn't accept post"):
        response = client.command('POST', 'http://webdocs.cs.ualberta.ca/~hazelcam/', {})
        assert response.code >= 400, response.code
        assert response.code < 500, response.code

    percent_test = '/ "<>^`{}/☃'

    # buttercup is frequently down, so we run the same checks against a local
    # copy of it (echo-server.py) that is shipped with the starter code.
    echo_urls = []
    local_echo_url = start_local_echo_server(tester)
    if local_echo_url is not None:
        echo_urls.append(local_echo_url)
    if os.environ.get('TEST_BUTTERCUP', False):
        echo_urls += ["http://buttercup.cs.ualberta.ca:9000/", "http://buttercup.cs.ualberta.ca/test/"]

    for buttercup_url in echo_urls:
        try:
            buttercup = get(buttercup_url)
            assert buttercup.status == 200, buttercup.status
        except Exception as e:
            tester.print_indented(str(e))
            tester.print_indented(f"{buttercup_url} isn't working :(... please tell Dr. Campbell to restart it")
            time.sleep(5)
        else:
            with tester("your client does percent-encoding in path"):
                url = buttercup_url + percent_test[1:]
                response = client.command('GET', url, {})
                assert response.code == 200, response.code
                assert '/%20%22%3C%3E%5E%60%7B%7D/%E2%98%83' in response.body.upper()
            
            with tester("your client does GET with arg"):
                url = buttercup_url
                key = hex(random.randint(0, MAX_SAFE_INT))
                val = hex(random.randint(0, MAX_SAFE_INT))
                response = client.command('GET', url, {key: val})
                assert response.code == 200, response.code
                wanted = f"&quot;{key}&quot;: &quot;{val}&quot;"
                assert wanted in response.body, f"wanted: {wanted}"

            with tester("your client does POST with arg"):
                url = buttercup_url
                key = hex(random.randint(0, MAX_SAFE_INT))
                val = hex(random.randint(0, MAX_SAFE_INT))
                response = client.command('POST', url, {key: val})
                assert response.code == 200, response.code
                wanted = f"<code>{key}</code>"
                assert wanted in response.body, f"wanted: {wanted}"
                wanted = f"<code>{val}</code>"
                assert wanted in response.body, f"wanted: {wanted}"

            with tester("your client does POST with arg and percentencoding"):
                url = buttercup_url
                response = client.command('POST', url, {"😀`": "😆/", "🙂{": "😊}"})
                assert response.code == 200, response.code
                wanted = f"<code>😀`</code>"
                assert wanted in response.body, f"wanted: {wanted}"
                wanted = f"<code>😆/</code>"
                assert wanted in response.body, f"wanted: {wanted}"
                wanted = "%F0%9F%98%80%60=%F0%9F%98%86%2F"
                assert wanted in response.body.upper(), f"wanted: {wanted}"
                wanted = "<code>🙂{</code>"
                assert wanted in response.body, f"wanted: {wanted}"
                wanted = "<code>😊}</code>"
                assert wanted in response.body, f"wanted: {wanted}"

            with tester("your client does GET with arg and percentencoding"):
                url = buttercup_url
                response = client.command('GET', url, {"☺️^": "😛/", "🤔<": "😎>"})
                assert response.code == 200, response.code
                wanted = f"&quot;☺️^&quot;: &quot;😛/&quot;"
                assert wanted in response.body, f"wanted: {wanted}"
                wanted = f"&quot;🤔&lt;&quot;: &quot;😎&gt;&quot;"
                assert wanted in response.body, f"wanted: {wanted}" + response.body

            with tester("your client can handle 301"):
                response = client.command('GET', url+'redirect/301/', {})
                assert response.code == 301, response.code

        
    if not os.environ.get('NO_PY1_TESTS', False):
        py1_url = "http://webdocs.cs.ualberta.ca/~hindle1/1.py"
        try:    
            py1 = get(py1_url)
            assert py1.status == 200, py1.status
        except Exception as e:
            tester.print_indented(str(e))
            tester.print_indented("1.py isn't working :(... please tell Dr. Hindle to fix it")
            time.sleep(5)
        else:
            with tester("your client does percent-encoding in path (1.py)"):
                url = py1_url + '/ "<>^`{}/☃'
                response = client.command('GET', url, {})
                assert response.code == 200, response.code
                assert '/%20%22%3C%3E%5E%60%7B%7D/%E2%98%83' in response.body.upper()
    
    cgi2_url = "http://webdocs.cs.ualberta.ca/~hindle1/2.cgi"
    try:
        cgi2 = get(cgi2_url)
        assert cgi2.status == 200, cgi2.status
    except Exception as e:
        tester.print_indented(str(e))
        tester.print_indented("2.cgi isn't working :(... please tell Dr. Hindle to fix it")
        time.sleep(5)
    else:
        with tester("your client does percent-encoding in path (2.cgi)"):
            url = cgi2_url + '/ "<>^`{}/☃'
            response = client.command('GET', url, {})
            assert response.code == 200, response.code
            assert '/%20%22%3C%3E%5E%60%7B%7D/%E2%98%83' in response.body.upper()
    
    typicode_url = "http://jsonplaceholder.typicode.com/posts"
    typicode_title = "qui est esse"
    try:
        typicode = get(typicode_url)
        assert typicode.status == 200, typicode.status
        loaded = json.loads(typicode.read())
        found = False
        for i in loaded:
            if i["title"] == typicode_title:
                found = True
        assert found
    except Exception as e:
        tester.print_indented(str(e))
        tester.print_indented("typicode isn't working")
        time.sleep(5)
    else:
        with tester("your client can get query params with percent encoding"):
            respone = client.command('GET', typicode_url, {'title': 'qui est esse'})
            assert respone.code == 200
            body = json.loads(respone.body)
            assert len(body) == 1, len(body)
            assert body[0]["title"] == typicode_title
    
    with tester("Starting test server..."):
        tester.print_indented("this should always work or the test script itself is broken")
        test_server_port = random.randrange(8900, 8999)
        test_server_key = random.randrange(0, MAX_SAFE_INT)
        ipv6_server_key = random.randrange(0, MAX_SAFE_INT)
        test_server_process = Process(target=test_server, args=('127.0.0.1', test_server_port, test_server_key))
        ipv6_server_process = Process(target=test_server, args=('::1', test_server_port, ipv6_server_key))
        test_server_process.start()
        time.sleep(0.5)
        ipv6_server_process.start()
        time.sleep(0.5)
        test_server_base = f"http://localhost:{test_server_port}/"

        def cleanup_test_server():
            tester.print("Killing test server...")
            test_server_process.kill()
            test_server_process.join(1)
            ipv6_server_process.kill()
            ipv6_server_process.join(1)
            tester.print("KILLED")
            assert not test_server_process.is_alive()
        tester.cleanup.append(cleanup_test_server)
        
        ipv4_test_server_base = f"http://127.0.0.1:{test_server_port}/"
        ipv6_test_server_base = f"http://[::1]:{test_server_port}/"


        with tester("get index.html directly from test server"):
            tester.print_indented("this should always work or the test script itself is broken")
            response = get("/index.html")

            with tester("Response 200 OK"):
                tester.print_indented("this should always work or the test script itself is broken")
                assert response.status == 200, f"Expected code 200 got {response.status}"
                assert response.reason == "OK"
            
            with tester("Content is accurate"):
                tester.print_indented("this should always work or the test script itself is broken")
                same_text(index_html, response.read())
            
            check_mime("text/html", response)

    def check_host_header(body, base, port):
        if base == test_server_base:
            assert (body['headers']['host'] == 'localhost' or body['headers']['host'] == f'localhost:{port}')
        elif base == ipv4_test_server_base:
            assert (body['headers']['host'] == '127.0.0.1' or body['headers']['host'] == f'127.0.0.1:{port}')
        else:
            assert (body['headers']['host'] == '::1' or body['headers']['host'] == '[::1]' or body['headers']['host'] == f'[::1]:{port}'), repr(body['headers']['host'])

    for base in [test_server_base, ipv4_test_server_base, ipv6_test_server_base]:
        with tester(f"get {base}"):
            response = client.command('GET', base, {})
            assert response.code == 200
        
            with tester("is response the index?"):
                same_text(index_html, response.body)
            
            url = relate(base, 'echo')
            with tester(f"checking echo-back {url}"):
                response = client.command('GET', url, {})
                assert response.code == 200
                body = json.loads(response.body)
                assert body['command'] == 'GET'
                assert body['server_path'] == '/echo'
                assert body['request_version'] == 'HTTP/1.1' 
                check_host_header(body, base, test_server_port)
                assert len(body['duplicate_headers']) == 0
                assert body['path'] == '/echo'

            k = random.choice('ABCDEFGHIJKLMNOPQRSTUV')
            v = random.choice('abcdefghijklmnopqrstuv')
            args = { k: v }
            with tester(f"checking echo-back {url}"):
                response = client.command('GET', url, args)
                assert response.code == 200
                body = json.loads(response.body)
                assert body['command'] == 'GET'
                assert body['server_path'] == f'/echo?{k}={v}'
                assert body['request_version'] == 'HTTP/1.1' 
                check_host_header(body, base, test_server_port)
                assert len(body['duplicate_headers']) == 0
                assert body['path'] == '/echo'
                assert body['query'] == f"{k}={v}", repr(body["query"])

def main():
    tester = Tester()
    tester.run(one_giant_function)

if __name__ == "__main__":
    main()