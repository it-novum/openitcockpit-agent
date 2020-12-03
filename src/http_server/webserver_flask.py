from filesystem import Filesystem
from config import Config
from agent_log import AgentLog
from check_result_store import CheckResultStore
from http_server.daemon_threaded_http_server import DaemonThreadedHTTPServer
from http_server.agent_request_handler import AgentRequestHandler
from certificates import Certificates
from main_thread import MainThread
import ssl
import json
import traceback

import socket

from flask import Flask, Response
from flask import request
from werkzeug.serving import make_server

# todo implement basic auth ?
class WebserverFlask:

    def __init__(self, config, agent_log, check_store, main_thread, certificates):
        self.Config: Config = config
        self.agent_log: AgentLog = agent_log
        self.check_store: CheckResultStore = check_store
        self.main_thread: MainThread = main_thread
        self.certificates: Certificates = certificates

        self.app = Flask(__name__)

        # Setup routs
        self.app.add_url_rule('/', '/', self.handle_request_check_data, methods=['GET'])
        self.app.add_url_rule('/getCsr', '/getCsr', self.handle_request_csr, methods=['GET'])
        self.app.add_url_rule('/config', '/config', self.handle_request_config, methods=['GET', 'POST'])
        self.app.add_url_rule('/updateCrt', '/updateCrt', self.handle_request_update_cert, methods=['POST'])

        # todo comment development reload
        self.app.add_url_rule('/reload', '/reload', self.handle_request_reload, methods=['GET'])

        self.enable_ssl = False
        if Filesystem.file_readable(
                self.Config.config.get('default', 'certfile', fallback=False)) and Filesystem.file_readable(
            self.Config.config.get('default', 'keyfile', fallback=False)):
            self.enable_ssl = True

        self.protocol = 'http'
        if (self.enable_ssl):
            self.protocol = 'https'

        self.server_address = {
            'address': self.Config.config.get('default', 'address', fallback='0.0.0.0'),
            'port': self.Config.config.getint('default', 'port', fallback=3333)
        }

    def handle_request_check_data(self):
        check_results = self.check_store.get_store_for_json_response()
        return self.app.response_class(
            response=json.dumps(check_results).encode(),
            status=200,
            mimetype='application/json'
        )

    def handle_request_csr(self):
        data = {}
        if self.Config.autossl:
            data['csr'] = self.certificates.get_csr().decode("utf-8")
        else:
            data['csr'] = "disabled"

        return self.app.response_class(
            response=json.dumps(data).encode(),
            status=200,
            mimetype='application/json'
        )

    def handle_request_config(self):
        if request.method == 'POST':
            response = {
                'success': False
            }

            data = request.get_data()

            if self.Config.config.getboolean('default', 'config-update-mode', fallback=False) is True:
                if self.Config.set_new_config_from_dict(data) is True:
                    self.main_thread.trigger_reload()
                    response['success'] = True

            return self.app.response_class(
                response=json.dumps(response).encode(),
                status=200,
                mimetype='application/json'
            )
        else:
            # GET Request
            config = {}

            if self.Config.config.getboolean('default', 'config-update-mode', fallback=False) is True:
                config = self.Config.get_config_as_dict()

            return self.app.response_class(
                response=json.dumps(config).encode(),
                status=200,
                mimetype='application/json'
            )

    def handle_request_reload(self):
        self.main_thread.trigger_reload()
        return self.app.response_class(
            response=json.dumps('reloading'),
            status=200,
            mimetype='application/json'
        )

    def handle_request_update_cert(self):
        # Save new SSL certificate
        response = {
            'success': False
        }
        update_sucessfully = False
        try:
            jdata = json.loads(request.get_data().decode('utf-8'))
            jxdata = json.loads(jdata)
            if 'signed' in jdata and 'ca' in jdata:
                if self.certificates.store_cert_file(jxdata['signed']) and \
                        self.certificates.store_ca_file(jxdata['ca']):
                    update_sucessfully = True
        except:
            self.agent_log.stacktrace(traceback.format_exc())

        if update_sucessfully is True:
            response['success'] = True
            # Reload all threads to enable the SSL certificate
            self.main_thread.trigger_reload()

        return self.app.response_class(
            response=json.dumps(response).encode(),
            status=200,
            mimetype='application/json'
        )

    def start_webserver(self):
        self.ssl_context = None

        if self.enable_ssl:
            # Just enable HTTPS
            self.agent_log.info('SSL Enabled')
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            self.ssl_context.load_cert_chain(
                certfile=self.Config.config.get('default', 'certfile'),
                keyfile=self.Config.config.get('default', 'keyfile')
            )
        elif self.Config.autossl and \
                Filesystem.file_readable(self.Config.config.get('default', 'autossl-key-file')) and \
                Filesystem.file_readable(self.Config.config.get('default', 'autossl-crt-file')) and \
                Filesystem.file_readable(self.Config.config.get('default', 'autossl-ca-file')):

            self.protocol = 'https'
            # Enable HTTPS with certificate authentication
            self.agent_log.info('SSL with custom certificate enabled')

            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            self.ssl_context.load_cert_chain(
                certfile=self.Config.config.get('default', 'autossl-crt-file'),
                keyfile=self.Config.config.get('default', 'autossl-key-file')
            )

            # Request client certificate
            self.ssl_context.verify_mode = ssl.CERT_REQUIRED

            # Load CA certificates used for validating the peer's certificate
            self.ssl_context.load_verify_locations(
                cafile=self.Config.config.get('default', 'autossl-ca-file'),
                capath=None,
                cadata=None
            )

        # Get Webserver object
        self.srv = make_server(
            self.server_address['address'],
            self.server_address['port'],
            self.app,
            ssl_context=self.ssl_context
        )
        self.ctx = self.app.app_context()
        self.ctx.push()

        self.agent_log.info("Server started at %s://%s:%s with a check interval of %d seconds" % (
            self.protocol,
            self.server_address['address'],
            self.server_address['port'],
            self.Config.config.getint('default', 'interval', fallback=5)
        ))

