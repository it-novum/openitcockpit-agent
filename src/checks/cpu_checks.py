import os
import traceback

import psutil

from checks.default_check import DefaultCheck


class CpuChecks(DefaultCheck):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.key_name = "cpu_checks_combined"

    def run_check(self) -> dict:
        self.agent_log.verbose('Running CPU checks')

        cpu_total_percentage_detailed = None
        cpu_total_percentage = None
        cpu_percentage = None
        cpu_percentage_detailed = None
        system_load_avg = []

        try:
            if hasattr(psutil, "getloadavg"):
                system_load_avg = psutil.getloadavg()
            elif hasattr(os, "getloadavg"):
                system_load_avg = os.getloadavg()
        except:
            self.agent_log.error("Could not get average system load!")
            self.agent_log.stacktrace(traceback.format_exc())

        if self.Config.config.getboolean('default', 'cpustats', fallback=True):
            # CPU #
            cpu_total_percentage = psutil.cpu_percent()
            cpu_percentage = psutil.cpu_percent(interval=0, percpu=True)

            cpu = psutil.cpu_times_percent(interval=0, percpu=False)
            cpu_total_percentage_detailed = cpu._asdict()

            cpu_percentage_detailed = [dict(cpu._asdict()) for cpu in
                                       psutil.cpu_times_percent(interval=0, percpu=True)]

        out = {
            'system_load': system_load_avg,
            'cpu_total_percentage': cpu_total_percentage,
            'cpu_percentage': cpu_percentage,
            'cpu_total_percentage_detailed': cpu_total_percentage_detailed,
            'cpu_percentage_detailed': cpu_percentage_detailed
        }

        return out
