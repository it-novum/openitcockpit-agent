import os
import traceback

import psutil

from checks.Check import Check

from utils.operating_system import OperatingSystem


class CpuChecks(Check):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.operating_system = OperatingSystem()

        self.key_name = "cpu_checks_combined"

    def run_check(self) -> dict:
        self.agent_log.verbose('Running CPU checks')

        cpuTotalPercentage = None
        cpuPercentage = None
        cpuPercentageDetailed = None
        if self.Config.config.getboolean('default', 'cpustats', fallback=True):
            # CPU #
            cpuTotalPercentage = psutil.cpu_percent()
            cpuPercentage = psutil.cpu_percent(interval=0, percpu=True)

            cpu = psutil.cpu_times_percent(interval=0, percpu=False)
            cpuTotalPercentageDetailed = cpu._asdict()

            cpuPercentageDetailed = [dict(cpu._asdict()) for cpu in
                                     psutil.cpu_times_percent(interval=0, percpu=True)]

        system_load_avg = []
        try:
            if hasattr(psutil, "getloadavg"):
                system_load_avg = psutil.getloadavg()
            elif hasattr(os, "getloadavg"):
                system_load_avg = os.getloadavg()
        except:
            self.agent_log.error("Could not get average system load!")
            self.agent_log.stacktrace(traceback.format_exc())

        out = {
            'system_load': system_load_avg,
        }

        if self.Config.config.getboolean('default', 'cpustats', fallback=True):
            out['cpu_total_percentage'] = cpuTotalPercentage
            out['cpu_percentage'] = cpuPercentage
            out['cpu_total_percentage_detailed'] = cpuTotalPercentageDetailed
            out['cpu_percentage_detailed'] = cpuPercentageDetailed

        return out.copy()
