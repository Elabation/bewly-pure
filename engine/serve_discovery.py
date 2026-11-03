"""Open the locally built page with working lazy search, without dependencies."""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import webbrowser


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        url = "http://127.0.0.1:{}/god-shelf.html".format(server.server_port)
        print(url, flush=True)
        webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
