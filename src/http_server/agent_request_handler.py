import json
import traceback
from http.server import BaseHTTPRequestHandler

from agent_log import AgentLog
from certificates import Certificates
from check_result_store import CheckResultStore
from config import Config
from main_thread import MainThread


class AgentRequestHandler(BaseHTTPRequestHandler):
    # todo I don't like this type of dependency injection very much
    check_store = None  # type: CheckResultStore
    config = None  # type: Config
    certificates = None  # type: Certificates
    agent_log = None  # type: AgentLog
    main_thread = None  # type: MainThread

    def _set_200_ok_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def _set_401_unauthorized_headers(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=')
        self.send_header('Content-type', 'text/html')

        self.end_headers()

    def _process_get_request(self):
        self._set_200_ok_headers()

        if self.path == "/":
            check_results = self.check_store.get_store_for_json_response()
            self.wfile.write(json.dumps(check_results).encode())
        elif self.path == "/config" and self.config.config.getboolean('default', 'config-update-mode',
                                                                      fallback=False) is True:
            config = self.config.get_config_as_dict()
            self.wfile.write(json.dumps(config).encode())
        elif self.path == "/getCsr":
            data = {}
            if self.config.autossl:
                data['csr'] = self.certificates.get_csr().decode("utf-8")
            else:
                data['csr'] = "disabled"
            self.wfile.write(json.dumps(data).encode())

        # Todo remove development reload
        # elif self.path == "/reload":
        #    # Reload all threads to enable the new config
        #    self.main_thread.trigger_reload()

    def _process_post_request(self, data):
        response = {
            'success': False
        }

        if self.path == "/config" and self.config.config.getboolean('default', 'config-update-mode',
                                                                    fallback=False) is True:
            if self.config.set_new_config_from_dict(data) is True:
                response['success'] = True
                # Reload all threads to enable the new config
                self.main_thread.trigger_reload()


        elif self.path == "/updateCrt" and self.config.autossl:
            # Save new SSL certificate
            update_sucessfully = False
            try:
                jdata = json.loads(data.decode('utf-8'))
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

        self._set_200_ok_headers()
        self.wfile.write(json.dumps(response).encode())

    def do_GET(self):
        """
        Call back function which gets called by the webserver whenever a GET request gets received
        """
        try:
            if 'auth' in self.config.config['default']:
                if str(self.config.config['default']['auth']).strip() and self.headers.get('Authorization') == None:
                    self._set_401_unauthorized_headers()
                    self.wfile.write('no auth header received'.encode())
                elif self.headers.get('Authorization') == 'Basic ' + self.config.config['default']['auth'] or \
                        self.config.config['default']['auth'] == "":
                    self._process_get_request()
                elif str(self.config.config['default']['auth']).strip():
                    self._set_401_unauthorized_headers()
                    self.wfile.write(self.headers.get('Authorization').encode())
                    self.wfile.write('not authenticated'.encode())
            else:
                self._process_get_request()
        except:
            self.agent_log.error('Error while processing GET request')
            self.agent_log.stacktrace(traceback.format_exc())

    def do_POST(self):
        """
        Call back function which gets called by the webserver whenever a POST request gets received
        """
        try:
            if 'auth' in self.config.config['default']:
                if str(self.config.config['default']['auth']).strip() and self.headers.get('Authorization') is None:
                    self._set_401_unauthorized_headers()
                    self.wfile.write('no auth header received'.encode())
                elif self.headers.get('Authorization') == 'Basic ' + self.config.config['default']['auth'] or \
                        self.config.config['default']['auth'] == "":
                    self.wfile.write(json.dumps(
                        self._process_post_request(data=self.rfile.read(int(self.headers['Content-Length'])))).encode())
                elif str(self.config.config['default']['auth']).strip():
                    self._set_401_unauthorized_headers()
                    self.wfile.write(self.headers.get('Authorization').encode())
                    self.wfile.write('not authenticated'.encode())
            else:
                self._process_post_request(data=self.rfile.read(int(self.headers['Content-Length'])))

        except:
            self.agent_log.error('Error while processing POST request')
            self.agent_log.stacktrace(traceback.format_exc())
