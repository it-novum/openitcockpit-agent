import platform
import time
import traceback
import psutil

from checks.default_check import DefaultCheck
from utils.operating_system import OperatingSystem


class AgentChecks(DefaultCheck):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)

        self.key_name = "agent"

    def run_check(self) -> dict:
        self.agent_log.verbose('Fetching agent information')

        uptime = 0
        try:
            uptime = int(time.time() - psutil.boot_time())
        except:
            self.agent_log.error("Could not get system uptime!")
            self.agent_log.stacktrace(traceback.format_exc())

        try:
            agent = {
                'last_updated': time.ctime(),
                'last_updated_timestamp': round(time.time()),
                'system': platform.system(),
                'system_uptime': uptime,
                'kernel_version': platform.release(),
                'mac_version': platform.mac_ver()[0],
                'agent_version': self.Config.agent_version,
                'temperature_unit': 'F' if self.Config.temperatureIsFahrenheit else 'C'
            }
        except:
            agent = {
                'last_updated': time.ctime(),
                'last_updated_timestamp': round(time.time()),
                'system_uptime': uptime,
                'agent_version': self.Config.agent_version,
                'temperature_unit': 'F' if self.Config.temperatureIsFahrenheit else 'C'
            }

        return agent.copy()
