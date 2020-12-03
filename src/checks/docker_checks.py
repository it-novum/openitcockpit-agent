import subprocess
import time
import traceback

from checks.Check import Check
from operating_system import OperatingSystem


class DockerChecks(Check):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.operating_system = OperatingSystem()

        self.key_name = "dockerstats"

        self.docker_stats_data = {}

    def run_check(self) -> dict:
        """Function that starts as a thread to run the docker status check

        Linux only!

        Function that runs a docker command (as python subprocess) to get a status result for each running docker container.

        Parameters
        ----------
        timeout
            Command timeout in seconds

        """

        timeout = self.check_params['timeout']

        if self.Config.verbose:
            self.agent_log.verbose(
                'Start docker status check with timeout of %ss' % (str(timeout))
            )

        tmp_docker_stats_result = ''
        self.docker_stats_data['running'] = "true"

        docker_stats_command = 'docker stats --no-stream --format "stats;{{.ID}};{{.Name}};{{.CPUPerc}};{{.MemUsage}};{{.MemPerc}};{{.NetIO}};{{.BlockIO}};{{.PIDs}}"'
        if self.operating_system.isWindows() is True:
            docker_stats_command = 'docker stats --no-stream --format "stats;{{.ID}};{{.Name}};{{.CPUPerc}};{{.MemUsage}};;{{.NetIO}};{{.BlockIO}};"'  # fill not existing 'MemPerc' and 'PIDs' with empty ; separated value
        docker_container_list_command = 'docker container list -a -s --format "cl;{{.ID}};{{.Status}};{{.Size}};{{.Image}};{{.RunningFor}};{{.Names}}"'

        try:
            p = subprocess.Popen(docker_stats_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            p2 = subprocess.Popen(docker_container_list_command, shell=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)

            try:
                stdout, stderr = p.communicate(timeout=int(timeout))
                stdout2, stderr2 = p2.communicate(timeout=int(timeout))
                p.poll()
                p2.poll()
                if stdout:
                    tmp_docker_stats_result = tmp_docker_stats_result + stdout.decode()
                if stdout2:
                    tmp_docker_stats_result = tmp_docker_stats_result + stdout2.decode()
                if stderr:
                    stderr = stderr.decode()
                if stderr2:
                    stderr2 = stderr2.decode()

                self.docker_stats_data['error'] = None if str(stderr) == 'None' else str(stderr)
                self.docker_stats_data['error'] = None if str(stderr) == 'None' and str(stderr2) == 'None' else str(
                    stderr2)
                self.docker_stats_data['returncode'] = p.returncode
            except subprocess.TimeoutExpired:
                self.agent_log.error('Docker status check timed out')
                p.kill()  # not needed; just to be sure
                p2.kill()
                self.docker_stats_data['result'] = None
                self.docker_stats_data['error'] = 'Docker status check timeout after ' + str(timeout) + ' seconds'
                self.docker_stats_data['returncode'] = 124

        except:
            self.agent_log.error('An error occurred while running the docker status check!')
            self.agent_log.stacktrace(traceback.format_exc())

        if tmp_docker_stats_result != '' and self.docker_stats_data['returncode'] == 0:
            results = tmp_docker_stats_result.split('\n')
            sorted_data = []
            sorted_stats_data = []
            sorted_cl_data = []
            for result in results:
                if result.strip() != "":
                    try:
                        result_array = result.strip().split(';')
                        tmp_dict = {}
                        if result_array[0] == 'stats':
                            tmp_dict['id'] = result_array[1]
                            tmp_dict['name'] = result_array[2]
                            tmp_dict['cpu_percent'] = result_array[3]
                            tmp_dict['memory_usage'] = result_array[4]
                            tmp_dict['memory_percent'] = result_array[5]
                            tmp_dict['net_io'] = result_array[6]
                            tmp_dict['block_io'] = result_array[7]
                            tmp_dict['pids'] = result_array[8]
                            sorted_stats_data.append(tmp_dict)
                        if result_array[0] == 'cl':
                            tmp_dict['id'] = result_array[1]
                            tmp_dict['status'] = result_array[2]
                            tmp_dict['size'] = result_array[3]
                            tmp_dict['image'] = result_array[4]
                            tmp_dict['created'] = result_array[5]
                            tmp_dict['name'] = result_array[6]
                            sorted_cl_data.append(tmp_dict)
                    except:
                        self.agent_log.error(
                            "An error occurred while processing the docker check output! Seems like there are no docker containers.")
                        self.agent_log.stacktrace(traceback.format_exc())

            for cl_data in sorted_cl_data:
                tmp_dict = cl_data

                for stats_data in sorted_stats_data:
                    if stats_data['id'] == cl_data['id']:
                        tmp_dict['name'] = stats_data['name']
                        tmp_dict['cpu_percent'] = stats_data['cpu_percent']
                        tmp_dict['memory_usage'] = stats_data['memory_usage']
                        tmp_dict['memory_percent'] = stats_data['memory_percent']
                        tmp_dict['net_io'] = stats_data['net_io']
                        tmp_dict['block_io'] = stats_data['block_io']
                        tmp_dict['pids'] = stats_data['pids']
                sorted_data.append(tmp_dict)

            self.docker_stats_data['result'] = sorted_data
            self.docker_stats_data['last_updated_timestamp'] = round(time.time())
            self.docker_stats_data['last_updated'] = time.ctime()
        elif self.docker_stats_data['error'] is None and tmp_docker_stats_result != "":
            self.docker_stats_data['error'] = tmp_docker_stats_result

        self.agent_log.verbose('Docker status check finished')
        del self.docker_stats_data['running']

        return self.docker_stats_data.copy()
