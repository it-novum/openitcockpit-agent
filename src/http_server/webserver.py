from src.filesystem import Filesystem
from src.config import Config
from src.agent_log import AgentLog
from src.check_result_store import CheckResultStore
from src.http_server.daemon_threaded_http_server import DaemonThreadedHTTPServer
from src.http_server.agent_request_handler import AgentRequestHandler
import ssl
import time


class Webserver:

    def __init__(self, config, agent_log, check_store):
        self.Config: Config = config
        self.agent_log: AgentLog = agent_log
        self.check_store: CheckResultStore = check_store

        AgentRequestHandler.check_store = check_store

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

    def loop(self):

        webserver_stop_requested = False

        while not webserver_stop_requested:
            print("Loopy?")
            try:
                self.httpd.handle_request()
            except:
                self.agent_log.error('Webserver died, try to restart ...')

            time.sleep(1)

        del self.httpd
        self.agent_log.info('Stopped permanent_webserver_thread')

    def start_webserver(self):
        self.agent_log.info("Starting webserver on %s:%s" % (
            self.Config.config.get('default', 'address', fallback='0.0.0.0'),
            self.Config.config.getint('default', 'port', fallback=3333)
        ))

        self.httpd = DaemonThreadedHTTPServer(self.server_address, AgentRequestHandler)

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
                self.protocol,
                self.Config.config.get('default' 'address', fallback='0.0.0.0'),
                self.Config.config.getint('default', 'port', fallback=3333),
                self.Config.config.getint('default', 'interval', fallback=5)
            ))
