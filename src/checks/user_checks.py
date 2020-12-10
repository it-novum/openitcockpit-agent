import traceback
import psutil

from checks.default_check import DefaultCheck


class UserChecks(DefaultCheck):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
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
