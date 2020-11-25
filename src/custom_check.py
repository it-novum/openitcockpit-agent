from src.agent_log import AgentLog
from src.check_result_store import CheckResultStore

import subprocess
import time
import shlex
import traceback


class CustomCheck:

    def __init__(self, custom_check, check_store, agent_log):
        self.custom_check: dict = custom_check
        self.check_store: CheckResultStore = check_store
        self.agent_log: AgentLog = agent_log

        self.timeout = self.custom_check['timeout']
        if self.timeout < 1:
            self.timeout = 1

    def execute_check(self) -> str:
        self.agent_log.verbose('Run custom check "%s"' % (self.custom_check['name']))

        check_result = {
            'result': 'Unknown error',
            'error': 'Unknown error',
            'returncode': -1,
            'last_updated': time.ctime(0),
            'last_updated_timestamp': 0
        }

        try:
            command_as_list = shlex.split(self.custom_check['command'])
        except:
            self.agent_log.error(
                'Custom check "%s" command line parse error. Plase see the logfile for more information (requires stacktrace enabled).'
            )
            self.agent_log.stacktrace(traceback.format_exc())

            output = 'Can not parse command line using shlex.split. Please see the logfile on the agent for more information (requires stacktrace enabled).'

            check_result = self._build_checkresult(
                output=output,
                error_output=output,
                returncode=124
            )

            self.check_store.store_custom_check(self.custom_check['name'], check_result.copy())

            # Return the name of the current custom check as string so the main thread can mark this as executed
            return self.custom_check['name']

        # Try to run the command
        try:
            self.agent_log.debug('Execute command %s' % (str(command_as_list)))

            result = subprocess.run(
                command_as_list,
                capture_output=True,
                shell=False,  # It looks like PyInstaller will set this to False anyway
                timeout=self.timeout,
                stdin=subprocess.DEVNULL
            )

            check_result = self._build_checkresult(
                output=result.stdout.decode(),
                error_output=result.stderr.decode(),
                returncode=result.returncode,
            )

        except subprocess.TimeoutExpired:
            self.agent_log.verbose(
                'Custom check "%s" timed out after %ss' % (self.custom_check['command'], self.timeout)
            )

            check_result = self._build_checkresult(
                output='Command "' + self.custom_check['name'] + '" timed out after ' + str(self.timeout) + ' seconds',
                error_output='Command "' + self.custom_check['name'] + '" timed out after ' + str(self.timeout) + ' seconds',
                returncode=124
            )

        except FileNotFoundError as err:
            self.agent_log.verbose(
                'Custom check "%s" error: %s' % (self.custom_check['command'], str(err))
            )

            check_result = self._build_checkresult(
                output=str(err),
                error_output=str(err),
                returncode=127
            )

        except Exception:
            self.agent_log.error(
                'An error occurred while running custom check "%s"!' % (self.custom_check['name'])
            )
            self.agent_log.error(
                'Command line: %s' % (self.custom_check['command'])
            )
            self.agent_log.stacktrace(traceback.format_exc())

        self.check_store.store_custom_check(self.custom_check['name'], check_result.copy())

        # Return the name of the current custom check as string so the main thread can mark this as executed
        return self.custom_check['name']

    def _build_checkresult(self, output: str, error_output: str, returncode: int) -> dict:
        return {
            'result': output,
            'error': error_output,
            'returncode': returncode,
            'last_updated': time.ctime(),
            'last_updated_timestamp': round(time.time())
        }
