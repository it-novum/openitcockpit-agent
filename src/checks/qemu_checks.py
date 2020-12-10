import subprocess
import time
import traceback

from checks.Check import Check
from utils.operating_system import OperatingSystem


class QemuChecks(Check):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.operating_system = OperatingSystem()

        self.key_name = "qemustats"

        self.qemu_stats_data = {}

    def run_check(self) -> dict:
        """Function that starts as a thread to run the qemu status check

        Linux only! (beta)

        Function that runs a (ps) command (as python subprocess) to get a status result for each running qemu (kvm) virtual machine.

        Parameters
        ----------
        timeout
            Command timeout in seconds

        """

        timeout = self.check_params['timeout']

        if self.Config.verbose:
            self.agent_log.verbose(
                'Start qemu status check with timeout of %ss' % (str(timeout))
            )

        tmp_qemu_stats_result = None
        self.qemu_stats_data['running'] = "true"

        # regex source: https://gist.github.com/kitschysynq/867caebec581cee4c44c764b4dd2bde7
        # qemu_command = "ps -ef | awk -e '/qemu/ && !/awk/ && !/openitcockpit-agent/' | sed -e 's/[^/]*/\n/' -e 's/ -/\n\t-/g'" # customized (without secure character escape)
        qemu_command = "ps -ef | gawk -e '/qemu/ && !/gawk/ && !/openitcockpit-agent/' | sed -e 's/[^/]*/\\n/' -e 's/ -/\\n\\t-/g'"  # customized

        try:
            p = subprocess.Popen(qemu_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            try:
                stdout, stderr = p.communicate(timeout=int(timeout))
                p.poll()
                if stdout:
                    stdout = stdout.decode()
                if stderr:
                    stderr = stderr.decode()
                tmp_qemu_stats_result = str(stdout)
                self.qemu_stats_data['error'] = None if str(stderr) == 'None' else str(stderr)
                self.qemu_stats_data['returncode'] = p.returncode
            except subprocess.TimeoutExpired:
                self.agent_log.warning('Qemu status check timed out')
                p.kill()  # not needed; just to be sure
                self.qemu_stats_data['result'] = None
                self.qemu_stats_data['error'] = 'Qemu status check timeout after ' + str(timeout) + ' seconds'
                self.qemu_stats_data['returncode'] = 124

        except:
            self.agent_log.error('An error occurred while running the qemu status check!')
            self.agent_log.stacktrace(traceback.format_exc())

        if tmp_qemu_stats_result is not None and self.qemu_stats_data['returncode'] == 0:
            ordered_results = []
            qemuresults = tmp_qemu_stats_result.split('\n\n')
            for machine in qemuresults:
                machine_data = {}
                for line in machine.split('\n'):
                    line = line.strip()

                    if line.split(' ')[0].strip().startswith('-'):
                        option = line.split(' ')[0].strip()
                        arrayoption = option[1:]
                        if arrayoption not in machine_data:
                            machine_data[arrayoption] = line.split(option)[1].strip()
                        else:
                            if isinstance(machine_data[arrayoption], list):
                                machine_data[arrayoption].append(line.split(option)[1].strip())
                            else:
                                current_content = machine_data[arrayoption]
                                machine_data[arrayoption] = []
                                machine_data[arrayoption].append(current_content)
                                machine_data[arrayoption].append(line.split(option)[1].strip())

                ordered_results.append(machine_data)

            self.qemu_stats_data['result'] = ordered_results
            self.qemu_stats_data['last_updated_timestamp'] = round(time.time())
            self.qemu_stats_data['last_updated'] = time.ctime()

        elif self.qemu_stats_data['error'] is None and tmp_qemu_stats_result != "":
            if self.qemu_stats_data['returncode'] == 1 and tmp_qemu_stats_result.startswith('sed:'):
                self.qemu_stats_data['error'] = "No qemu machines running"
            else:
                self.qemu_stats_data['error'] = tmp_qemu_stats_result

        self.agent_log.verbose('Qemu status check finished')
        del self.qemu_stats_data['running']

        return self.qemu_stats_data.copy()
