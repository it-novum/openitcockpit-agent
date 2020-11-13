import json

from src.config import Config
from src.agent_log import AgentLog
from src.check_result_store import CheckResultStore
from src.filesystem import Filesystem
from src.certificates import Certificates

import urllib3
import requests
import traceback


class PushClient:

    def __init__(self, config, agent_log, check_store, certificates):
        self.Config: Config = config
        self.agent_log: AgentLog = agent_log
        self.check_store: CheckResultStore = check_store
        self.certificates: Certificates = certificates

    def send_check_results(self):
        try:

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'X-OITC-API ' + self.Config.push_config['apikey'],
            }

            check_data = self.check_store.get_store_for_json_response()
            data = {
                'checkdata': json.dumps(check_data),
                'hostuuid': self.Config.push_config['hostuuid']
            }

            if self.Config.autossl and Filesystem.file_readable(self.Config.config.get('default', 'autossl-crt-file')):
                data['checksum'] = self.certificates.get_cert_checksum()

            try:
                urllib3.disable_warnings()
            except:
                if self.Config.stacktrace:
                    traceback.print_exc()

            self.agent_log.verbose('Sending POST request with check results to %s' % self.Config.push_config['url'])

            # For debugging server
            # url = self.Config.push_config['url']

            # For production
            url = self.Config.push_config['url'] + '/agentconnector/updateCheckdata.json'

            response = requests.post(
                url,
                data=data,
                headers=headers,
                verify=False
            )

            # response_body = response.content.decode('utf-8')
            # print(response_body)

            if response.content.decode('utf-8').strip() != '':
                response_data = json.loads(response.content.decode('utf-8'))

                if 'receivedChecks' in response_data:
                    self.agent_log.verbose('openITCOCKPIT processed %d check results' % response_data['receivedChecks'])
                    if response_data['receivedChecks'] == 0:
                        self.agent_log.info('Agent maybe not trusted yet or no checks have been defined')



        except:
            self.agent_log.error('An error occurred while sending check results to openITCOCKPIT instance!')

            if self.Config.stacktrace:
                traceback.print_exc()
