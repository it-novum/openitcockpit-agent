import subprocess
import time
import traceback

from checks.default_check import DefaultCheck
from utils.operating_system import OperatingSystem


class SystemdChecks(DefaultCheck):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.key_name = "systemd_services"

        self.systemd_services_data = {}

    def run_check(self) -> dict:
        """Function that starts as a thread to run the systemd services check

        Linux only! (beta)

        Function that runs a (systemctl) command (as python subprocess) to get a status result for each registered systemd service.

        Parameters
        ----------
        timeout
            Command timeout in seconds

        """

        timeout = self.check_params['timeout']

        if self.Config.verbose:
            self.agent_log.verbose(
                'Start systemd services check with timeout of %ss' % (str(timeout))
            )

        self.systemd_services_data['running'] = "true"

        systemd_services = []
        if self.operating_system.linux and self.Config.config.getboolean('default',
                                                                             'systemdservices'):
            systemd_stats_command = "systemctl list-units --type=service --all --no-legend --no-pager --no-ask-password"
            try:
                tmp_systemd_stats_result = ''
                p = subprocess.Popen(systemd_stats_command, shell=True, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)

                try:
                    stdout, stderr = p.communicate(timeout=3)
                    p.poll()
                    if stdout:
                        tmp_systemd_stats_result = tmp_systemd_stats_result + stdout.decode()
                    if stderr:
                        stderr = stderr.decode()

                    self.systemd_services_data['error'] = None if str(stderr) == 'None' else str(stderr)
                    self.systemd_services_data['returncode'] = p.returncode
                except subprocess.TimeoutExpired:
                    self.agent_log.debug('systemd status check timed out')
                    p.kill()  # not needed; just to be sure
                    self.systemd_services_data['result'] = None
                    self.systemd_services_data['error'] = 'systemd status check timeout after 3 seconds'
                    self.systemd_services_data['returncode'] = 124

                if tmp_systemd_stats_result != '' and self.systemd_services_data['returncode'] == 0:
                    results = tmp_systemd_stats_result.split('\n')
                    for result in results:
                        if result.strip() != "":
                            try:
                                result_array_unsorted = result.strip().split(' ')
                                result_array_tmp = []
                                result_array = []
                                for i in range(len(result_array_unsorted)):
                                    if str(result_array_unsorted[i]) != "":
                                        result_array_tmp.append(result_array_unsorted[i])

                                for i in range(4):
                                    result_array.append(result_array_tmp[0])
                                    del result_array_tmp[0]

                                service_description = ''
                                for i in range(len(result_array_tmp)):
                                    service_description = service_description + result_array_tmp[i] + ' '

                                tmp_dict = {}
                                tmp_dict['unit'] = result_array[0]
                                tmp_dict['load'] = result_array[1]
                                tmp_dict['active'] = result_array[2]
                                tmp_dict['sub'] = result_array[3]
                                tmp_dict['desc'] = service_description.strip()
                                systemd_services.append(tmp_dict)
                            except:
                                self.agent_log.error("An error occurred while processing the systemd check output!")
                                self.agent_log.stacktrace(traceback.format_exc())

                    self.systemd_services_data['result'] = systemd_services
                    self.systemd_services_data['last_updated_timestamp'] = round(time.time())
                    self.systemd_services_data['last_updated'] = time.ctime()

            except:
                self.agent_log.error('An error occurred while running the systemd status check!')
                self.agent_log.stacktrace(traceback.format_exc())

        del self.systemd_services_data['running']
        self.agent_log.verbose('Systemd services check finished')

        return self.systemd_services_data.copy()
