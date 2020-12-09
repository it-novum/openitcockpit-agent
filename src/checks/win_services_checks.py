import traceback
import psutil

from checks.Check import Check
from operating_system import OperatingSystem


class WinServicesChecks(Check):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.operating_system = OperatingSystem()

        self.key_name = "windows_services"

    def run_check(self):
        self.agent_log.verbose('Running Windows services checks')

        windows_services = []
        try:
            for win_process in psutil.win_service_iter():
                windows_services.append(win_process.as_dict())
        except:
            self.agent_log.error("An error occurred during windows services check!")
            self.agent_log.stacktrace(traceback.format_exc())

        return windows_services