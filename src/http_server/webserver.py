from src.filesystem import Filesystem
from src.config import Config
from src.agent_log import AgentLog
from src.check_result_store import CheckResultStore
from src.http_server.daemon_threaded_http_server import DaemonThreadedHTTPServer
from src.http_server.agent_request_handler import AgentRequestHandler
from src.certificates import Certificates
from src.main_thread import MainThread
import ssl

import socket


class Webserver:

    def __init__(self, config, agent_log, check_store, main_thread, certificates):
        self.Config: Config = config
        self.agent_log: AgentLog = agent_log
        self.check_store: CheckResultStore = check_store
        self.main_thread: MainThread = main_thread
        self.certificates: Certificates = certificates

        # Dependency injection into AgentRequestHandler
        AgentRequestHandler.check_store = check_store
        AgentRequestHandler.config = config
        AgentRequestHandler.certificates = self.certificates
        AgentRequestHandler.agent_log = agent_log
        AgentRequestHandler.main_thread = main_thread

        self.enable_ssl = False
        if Filesystem.file_readable(
                self.Config.config.get('default', 'certfile', fallback=False)) and Filesystem.file_readable(
            self.Config.config.get('default', 'keyfile', fallback=False)):
            self.enable_ssl = True

        self.protocol = 'http'
        if (self.enable_ssl):
            self.protocol = 'https'
        self.server_address = (
            self.Config.config.get('default', 'address', fallback='0.0.0.0'),
            self.Config.config.getint('default', 'port', fallback=3333)
        )

    def start_webserver(self):
        self.agent_log.info("Starting webserver on %s:%s" % (
            self.Config.config.get('default', 'address', fallback='0.0.0.0'),
            self.Config.config.getint('default', 'port', fallback=3333)
        ))

        self.sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.server_address)
        self.sock.settimeout(5)
        self.sock.listen(5)

        self.httpd = DaemonThreadedHTTPServer(self.server_address, AgentRequestHandler)
        self.httpd.socket = self.sock

        if self.enable_ssl:
            self.agent_log.info('SSL Enabled')
            self.httpd.socket = ssl.wrap_socket(self.httpd.socket,
                                                keyfile=self.Config.config.get('default', 'keyfile'),
                                                certfile=self.Config.config.get('default', 'certfile'),
                                                server_side=True
                                                )
        elif self.Config.autossl and \
                Filesystem.file_readable(self.Config.config.get('default', 'autossl-key-file')) and \
                Filesystem.file_readable(self.Config.config.get('default', 'autossl-crt-file')) and \
                Filesystem.file_readable(self.Config.config.get('default', 'autossl-ca-file')):
            self.agent_log.info('SSL with custom certificate enabled')

            self.httpd.socket = ssl.wrap_socket(self.httpd.socket,
                                                keyfile=self.Config.config.get('default', 'autossl-key-file'),
                                                certfile=self.Config.config.get('default', 'autossl-crt-file'),
                                                ca_certs=self.Config.config.get('default', 'autossl-ca-file'),
                                                server_side=True,
                                                cert_reqs=ssl.CERT_REQUIRED
                                                )

            self.agent_log.info("Server started at %s://%s:%s with a check interval of %d seconds" % (
                'https',
                self.Config.config.get('default', 'address', fallback='0.0.0.0'),
                self.Config.config.getint('default', 'port', fallback=3333),
                self.Config.config.getint('default', 'interval', fallback=5)
            ))

    def loop(self):
        #self.httpd.timeout = 10
        #self.httpd.handle_timeout = lambda: (_ for _ in ()).throw(TimeoutError())

        self.run_loop = True

        while self.run_loop:
            try:
                self.httpd.handle_request()
            except TimeoutError:
                self.agent_log.error('Http SERVER TIMEOUT! Trigger reload of the agent')
                #self.run_loop = False
                #self.sock.shutdown(socket.SHUT_RDWR)
                #self.sock.close()
                #self.main_thread.trigger_reload()
    
    def shutdown(self):
        self.run_loop = False

