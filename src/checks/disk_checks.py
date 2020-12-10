import traceback
import psutil

from checks.Check import Check

from utils.operating_system import OperatingSystem


class DiskChecks(Check):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.operating_system = OperatingSystem()

        self.key_name = "disks"

    def run_check(self):
        self.agent_log.verbose('Running disk checks')

        disks = []
        # DISKS #
        try:
            for disk in psutil.disk_partitions():
                if self.operating_system.windows:
                    if 'cdrom' in disk.opts or disk.fstype == '':
                        # skip cd-rom drives with no disk in it; they may raise
                        # ENOENT, pop-up a Windows GUI error for a non-ready
                        # partition or just hang.
                        continue
                disks.append(dict(
                    disk=disk._asdict(),
                    usage=psutil.disk_usage(disk.mountpoint)._asdict()
                ))
        except:
            self.agent_log.error("Could not get system disks!")
            self.agent_log.stacktrace(traceback.format_exc())

        return disks
