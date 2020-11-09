from src.agent_log import AgentLog
from src.check_result_store import CheckResultStore

import subprocess


class CustomCheck:

    def __init__(self, custom_check, check_store, agent_log):
        self.custom_check: dict = custom_check
        self.check_store: CheckResultStore = check_store
        self.agent_log: AgentLog = agent_log

        self.timeout = self.custom_check['timeout']
        if self.timeout < 1:
            self.timeout = 1

    def execute_check(self):
        self.agent_log.verbose('Run custom check "%s"' % (self.custom_check['name']))

        check_result = {
            'result': 'Unknown error',
            'error': 'Unknown error',
            'returncode': -1
        }

        try:
            result = subprocess.run(
                self.custom_check['command'],
                capture_output=True,
                shell=True,
                timeout=self.timeout
            )

            check_result = {
                'result': result.stdout.decode(),
                'error': result.stderr.decode(),
                'returncode': result.returncode
            }

        except subprocess.TimeoutExpired:
            self.agent_log.verbose(
                'Custom check "%s" timed out after %ss' % (self.custom_check['command'], self.timeout)
            )

            check_result = {
                'result': 'Command "' + self.custom_check['name'] + '" timed out after ' +
                          str(self.timeout) + ' seconds',
                'error': 'Command "' + self.custom_check['name'] + '" timed out after ' +
                         str(self.timeout) + ' seconds',
                'returncode': 124
            }

        except Exception:
            self.agent_log.error(
                'An error occurred while running custom check "%s"!' % (self.custom_check['name'])
            )
            self.agent_log.error(
                'Command line: %s' % (self.custom_check['command'])
            )

        self.check_store.store_custom_check(self.custom_check['name'], check_result.copy())
