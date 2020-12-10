import sys
import traceback

import psutil

from checks.Check import Check

if sys.platform == 'win32' or sys.platform == 'win64':
    pass

from utils.operating_system import OperatingSystem


class NetStatsChecks(Check):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.operating_system = OperatingSystem()

        self.key_name = "net_stats"

    def run_check(self) -> dict:
        self.agent_log.verbose('Running network stats checks')

        net_stats = {}
        if hasattr(psutil, "net_if_stats"):
            try:
                net_stats = {device: data._asdict() for device, data in psutil.net_if_stats().items()}
            except:
                self.agent_log.error("Could not get network device stats!")
                self.agent_log.stacktrace(traceback.format_exc())

        return net_stats.copy()
