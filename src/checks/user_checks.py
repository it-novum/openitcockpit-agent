import traceback
import psutil

from checks.Check import Check
from utils.operating_system import OperatingSystem


class UserChecks(Check):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.operating_system = OperatingSystem()

        self.key_name = "users"

    def run_check(self):
        self.agent_log.verbose('Running users checks')

        users = []
        try:
            if hasattr(psutil, "users"):
                users = [user._asdict() for user in psutil.users()]
        except:
            self.agent_log.error("Could not get users, connected to the system!")
            self.agent_log.stacktrace(traceback.format_exc())

        return users
