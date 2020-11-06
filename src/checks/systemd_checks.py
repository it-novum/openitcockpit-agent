import traceback
import time
import subprocess

from src.checks.Check import Check
from src.operating_system import OperatingSystem


class SystemdChecks(Check):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.operating_system = OperatingSystem()

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

        self.agent_log.info(
            'Start systemd services check with timeout of %ss at %s' % (str(timeout), str(round(time.time()))))
        if self.Config.verbose:
            print(
                'Start systemd services check with timeout of %ss at %s' % (str(timeout), str(round(time.time()))))

        self.systemd_services_data['running'] = "true"

        systemd_services = []
        if self.operating_system.isLinux() is True and self.Config.config.getboolean('default',
                                                                                     'systemdservices') is True:
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
                                self.agent_log.error("An error occured while processing the systemd check output!")

                                if self.Config.stacktrace:
                                    traceback.print_exc()

                    self.systemd_services_data['result'] = systemd_services
                    self.systemd_services_data['last_updated_timestamp'] = round(time.time())
                    self.systemd_services_data['last_updated'] = time.ctime()

            except:
                self.agent_log.error('An error occured while running the systemd status check!')

                if self.Config.stacktrace:
                    traceback.print_exc()

        del self.systemd_services_data['running']
        self.agent_log.info('Systemd services check finished')

        return self.systemd_services_data.copy()
