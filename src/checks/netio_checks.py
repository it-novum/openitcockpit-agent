import time
import traceback

import psutil

from checks.Check import Check

from utils.operating_system import OperatingSystem


class NetIoChecks(Check):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.operating_system = OperatingSystem()

        self.key_name = "net_io"

        self.cached_netIO = {}

    def run_check(self) -> dict:
        self.agent_log.verbose('Running network IO checks')

        netIO = {}
        if hasattr(psutil, "net_io_counters"):
            try:
                netIO = {device: data._asdict() for device, data in psutil.net_io_counters(pernic=True).items()}
                netIO['timestamp'] = time.time()

                for device in netIO:
                    if device != "timestamp" and device in self.cached_netIO:

                        netIODiff = {}
                        netIODiff['timestamp'] = self.wrapdiff(float(self.cached_netIO['timestamp']),
                                                               float(netIO['timestamp']))

                        for attr in netIO[device]:
                            diff = self.wrapdiff(float(self.cached_netIO[device][attr]), float(netIO[device][attr]))
                            netIODiff[attr] = diff

                        if netIODiff['bytes_sent']:
                            netIO[device]['avg_bytes_sent_ps'] = float(
                                netIODiff['bytes_sent'] / netIODiff['timestamp'])
                        else:
                            netIO[device]['avg_bytes_sent_ps'] = 0

                        if netIODiff['bytes_recv']:
                            netIO[device]['avg_bytes_recv_ps'] = float(
                                netIODiff['bytes_recv'] / netIODiff['timestamp'])
                        else:
                            netIO[device]['avg_bytes_recv_ps'] = 0

                        if netIODiff['packets_sent']:
                            netIO[device]['avg_packets_sent_ps'] = float(
                                netIODiff['packets_sent'] / netIODiff['timestamp'])
                        else:
                            netIO[device]['avg_packets_sent_ps'] = 0

                        if netIODiff['packets_recv']:
                            netIO[device]['avg_packets_recv_ps'] = float(
                                netIODiff['packets_recv'] / netIODiff['timestamp'])
                        else:
                            netIO[device]['avg_packets_recv_ps'] = 0

                        if netIODiff['errin']:
                            netIO[device]['avg_errin'] = float(netIODiff['errin'] / netIODiff['timestamp'])
                        else:
                            netIO[device]['avg_errin'] = 0

                        if netIODiff['errout']:
                            netIO[device]['avg_errout'] = float(netIODiff['errout'] / netIODiff['timestamp'])
                        else:
                            netIO[device]['avg_errout'] = 0

                        if netIODiff['dropin']:
                            netIO[device]['avg_dropin'] = float(netIODiff['dropin'] / netIODiff['timestamp'])
                        else:
                            netIO[device]['avg_dropin'] = 0

                        if netIODiff['dropout']:
                            netIO[device]['avg_dropout'] = float(netIODiff['dropout'] / netIODiff['timestamp'])
                        else:
                            netIO[device]['avg_dropout'] = 0

                self.cached_netIO = netIO
            except:
                self.agent_log.error("Could not get network io stats!")
                self.agent_log.stacktrace(traceback.format_exc())

        return netIO.copy()
