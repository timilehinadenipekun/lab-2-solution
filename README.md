# Labsignment: HTTP

Assignment instructions [are on the course website](https://cmput404-fall2026.github.io/labs/http/).

## Files

| File | What it is |
| --- | --- |
| `httpclient.py` | **You write this.** Your HTTP/1.1 client. |
| `server.py` | **You write this.** Your HTTP/1.1 web server. |
| `free-tests.py` | The public test suite. Run it with `python3 free-tests.py`. Do not modify. |
| `echo-server.py` | A local echo server the tests use to check your client. Do not modify. |
| `www/` | Created by the tests. The directory your server serves files from. |

## Testing

```sh
python3 free-tests.py
```

You can also run the echo server by itself and poke at it with your own client,
curl, or a browser:

```sh
python3 echo-server.py          # http://localhost:9000/
python3 httpclient.py GET http://localhost:9000/ name value
```

## Write down any collaboration or citations that aren't in server.py here:


