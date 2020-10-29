from socketserver import ThreadingMixIn
from http.server import HTTPServer


class DaemonThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    daemon_threads = True
