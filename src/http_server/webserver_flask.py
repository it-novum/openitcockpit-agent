from src.filesystem import Filesystem
from src.config import Config
from src.agent_log import AgentLog
from src.check_result_store import CheckResultStore
from src.http_server.daemon_threaded_http_server import DaemonThreadedHTTPServer
from src.http_server.agent_request_handler import AgentRequestHandler
from src.certificates import Certificates
from src.main_thread import MainThread
import ssl
import json

import socket

from flask import Flask, Response
from werkzeug.serving import make_server


class WebserverFlask:

    def __init__(self, config, agent_log, check_store, main_thread, certificates):
        self.Config: Config = config
        self.agent_log: AgentLog = agent_log
        self.check_store: CheckResultStore = check_store
        self.main_thread: MainThread = main_thread
        self.certificates: Certificates = certificates

        self.app = Flask(__name__)

        self.app.add_url_rule('/', '/', self.callback)

    def callback(self, *args):
        check_results = self.check_store.get_store_for_json_response()
        return self.app.response_class(
            response=json.dumps(check_results).encode(),
            status=200,
            mimetype='application/json'
        )

    def start_webserver(self):
        self.srv = make_server('127.0.0.1', 33333, self.app)
        self.ctx = self.app.app_context()
        self.ctx.push()

    def loop(self):
        print('starting server')
        self.srv.serve_forever()

    def shutdown(self):
        print('shutdown server')
        self.srv.shutdown()
