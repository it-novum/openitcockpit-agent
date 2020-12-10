import time
import traceback

import psutil

from checks.default_check import DefaultCheck
from utils.operating_system import OperatingSystem


class DiskIoChecks(DefaultCheck):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.key_name = "disk_io"

        self.cached_diskIO = {}

    def run_check(self) -> dict:
        self.agent_log.verbose('Running disk IO checks')

        diskIO = {}
        if hasattr(psutil, "disk_io_counters"):
            try:
                # diskIOTotal = psutil.disk_io_counters(perdisk=False)._asdict()
                # diskIO = psutil.disk_io_counters(perdisk=True)
                diskIO = {disk: iops._asdict() for disk, iops in psutil.disk_io_counters(perdisk=True).items()}
                diskIO['timestamp'] = time.time()

                for disk in diskIO:
                    if disk != "timestamp" and disk in self.cached_diskIO:

                        diskIODiff = {}
                        diskIODiff['timestamp'] = self.wrapdiff(float(self.cached_diskIO['timestamp']),
                                                                float(diskIO['timestamp']))

                        for attr in diskIO[disk]:
                            diff = self.wrapdiff(float(self.cached_diskIO[disk][attr]), float(diskIO[disk][attr]))
                            diskIODiff[attr] = diff

                        diskIO[disk]['read_iops'] = diskIODiff['read_count'] / diskIODiff['timestamp']
                        diskIO[disk]['write_iops'] = diskIODiff['write_count'] / diskIODiff['timestamp']

                        tot_ios = diskIODiff['read_count'] + diskIODiff['write_count']
                        diskIO[disk]['total_iops'] = tot_ios / diskIODiff['timestamp']
                        # diskIO[disk]['tot_ticks'] = diskIODiff['busy_time']
                        # diskIO[disk]['interval'] = diskIODiff['timestamp']
                        if 'busy_time' in diskIODiff:
                            diskIO[disk]['load_percent'] = diskIODiff['busy_time'] / (
                                    diskIODiff['timestamp'] * 1000.) * 100.

                        if diskIODiff['read_count']:
                            diskIO[disk]['read_avg_wait'] = float(
                                diskIODiff['read_time'] / diskIODiff['read_count'])
                            diskIO[disk]['read_avg_size'] = float(
                                diskIODiff['read_bytes'] / diskIODiff['read_count'])
                        else:
                            diskIO[disk]['read_avg_wait'] = 0
                            diskIO[disk]['read_avg_size'] = 0

                        if diskIODiff['write_count']:
                            diskIO[disk]['write_avg_wait'] = float(
                                diskIODiff['write_time'] / diskIODiff['write_count'])
                            diskIO[disk]['write_avg_size'] = float(
                                diskIODiff['write_bytes'] / diskIODiff['write_count'])
                        else:
                            diskIO[disk]['write_avg_wait'] = 0
                            diskIO[disk]['write_avg_size'] = 0

                        if tot_ios:
                            diskIO[disk]['total_avg_wait'] = float(
                                (diskIODiff['read_time'] + diskIODiff['write_time']) / tot_ios)
                        else:
                            diskIO[disk]['total_avg_wait'] = 0

                self.cached_diskIO = diskIO
            except:
                self.agent_log.error("Could not get disk io stats!")
                self.agent_log.stacktrace(traceback.format_exc())

        return diskIO.copy()
