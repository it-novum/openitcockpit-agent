from http.server import HTTPServer
from socketserver import ThreadingMixIn


class DaemonThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    daemon_threads = True

    # def finish_request(self, request, client_address):
    #    request.settimeout(15)
    #    # "super" can not be used because BaseServer is not created from object
    #    HTTPServer.finish_request(self, request, client_address)
