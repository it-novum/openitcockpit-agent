import os
import sys
import traceback
import platform
import psutil
import time
from contextlib import contextmanager

from src.checks.Check import Check

if sys.platform == 'win32' or sys.platform == 'win64':
    import win32evtlog
    import win32evtlogutil
    import win32con
    import win32security  # To translate NT Sids to account names.

from src.operating_system import OperatingSystem


class DefaultChecks(Check):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.operating_system = OperatingSystem()

        self.key_name = "default_checks"

        self.cached_diskIO = {}
        self.cached_netIO = {}

    def run_check(self) -> dict:
        """Function to run the default checks

        Run default checks to get following information points.


        - disks (Storage devices with mountpoint, filesystem and storage space definitions)
        - disk_io (Read and write statistics of the storage devices)
        - net_io (Input and Outputstatistics of the network devices)
        - net_stats (Network devices including the possible speed, ...)
        - sensors (Connected sensors, e.g. temperature of the cpu, akku state)
        - cpu_total_percentage (Used CPU calculation time in percent)
        - cpu_percentage (Used cpu calculation time in percent per core)
        - cpu_total_percentage_detailed (Cpu calculation time in percent per system ressource)
        - cpu_percentage_detailed (Cpu calculation time in percent per system ressource per core)
        - system_load (System load 1, 5, 15 as array)
        - users (Users logged on to the system, their terminals (pid), login time)
        - memory (Memory information, total, used, active, buffered, ...)
        - swap (Swap information, total, used, ...)
        - processes (Information to running processes, cpu, memory, pid, ...)
        - agent (Agent version, last check time, system version, ...)
        - dockerstats (Docker containers, id, cpu, memory, block io, pid)
        - qemustats (Information to active QEMU virtual machines)


        Notice:

        Processes with id 0 or 1 are excluded of the process parent and child id check.
        There are the root processes on linux, macOS and windows.
        These checks are configurable: dockerstats, qemustats, cpustats, sensorstats, processstats, netstats, diskstats, netio, diskio, winservices.
        Average values and iops in netio and diskio checks are available after the second check goes through.


        Returns
        -------
        dict
            Object (dictionary) containing all the default check results

        """
        self.agent_log.verbose('Running default checks')

        # if verbose:
        #    print_lock.acquire()

        if self.Config.config.getboolean('default', 'cpustats', fallback=True):
            # CPU #
            cpuTotalPercentage = psutil.cpu_percent()
            cpuPercentage = psutil.cpu_percent(interval=0, percpu=True)

            cpu = psutil.cpu_times_percent(interval=0, percpu=False)
            cpuTotalPercentageDetailed = cpu._asdict()

            cpuPercentageDetailed = [dict(cpu._asdict()) for cpu in
                                     psutil.cpu_times_percent(interval=0, percpu=True)]

        uptime = 0
        try:
            uptime = int(time.time() - psutil.boot_time())
        except:
            self.agent_log.error("Could not get system uptime!")
            self.agent_log.stacktrace(traceback.format_exc())

        # totalCpus = psutil.cpu_count()
        # physicalCpus = psutil.cpu_count(logical=False)

        # cpuFrequency = psutil.cpu_freq()

        # MEMORY #

        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        disks = []
        if self.Config.config.getboolean('default', 'diskstats'):
            # DISKS #
            try:
                for disk in psutil.disk_partitions():
                    if self.operating_system.isWindows():
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

        diskIO = None
        if hasattr(psutil, "disk_io_counters") and self.Config.config.getboolean('default', 'diskio'):
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

        netIO = None
        if hasattr(psutil, "net_io_counters") and self.Config.config.getboolean('default', 'netio'):
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

        net_stats = None
        if hasattr(psutil, "net_if_stats") and self.Config.config.getboolean('default', 'netstats'):
            try:
                net_stats = {device: data._asdict() for device, data in psutil.net_if_stats().items()}
            except:
                self.agent_log.error("Could not get network device stats!")
                self.agent_log.stacktrace(traceback.format_exc())

        sensors = {}
        if self.Config.config.getboolean('default', 'sensorstats'):
            try:
                if hasattr(psutil, "sensors_temperatures") and self.operating_system.isWindows() is False:
                    sensors['temperatures'] = {}
                    for device, data in psutil.sensors_temperatures(
                            fahrenheit=self.Config.temperatureIsFahrenheit).items():
                        sensors['temperatures'][device] = []
                        for value in data:
                            sensors['temperatures'][device].append(value._asdict())
                else:
                    sensors['temperatures'] = {}
            except:
                self.agent_log.error("Could not get temperature sensor data!")
                self.agent_log.stacktrace(traceback.format_exc())

            try:
                if hasattr(psutil, "sensors_fans") and self.operating_system.isWindows() is False:
                    sensors['fans'] = {}
                    for device, data in psutil.sensors_fans().items():
                        sensors['fans'][device] = []
                        for value in data:
                            sensors['fans'][device].append(value._asdict())
                else:
                    sensors['fans'] = {}
            except:
                self.agent_log.error("Could not get fans sensor data!")
                self.agent_log.stacktrace(traceback.format_exc())

            try:
                if hasattr(psutil, "sensors_battery"):
                    sensors_battery = psutil.sensors_battery()
                    if sensors_battery is not None:
                        sensors['battery'] = sensors_battery._asdict()
                    else:
                        sensors['battery'] = {}
                else:
                    sensors['battery'] = {}
            except:
                self.agent_log.error("Could not get battery sensor data!")
                self.agent_log.stacktrace(traceback.format_exc())

        system_load_avg = []
        try:
            if hasattr(psutil, "getloadavg"):
                system_load_avg = psutil.getloadavg()
            elif hasattr(os, "getloadavg"):
                system_load_avg = os.getloadavg()
        except:
            self.agent_log.error("Could not get average system load!")
            self.agent_log.stacktrace(traceback.format_exc())

        users = []
        try:
            if hasattr(psutil, "users"):
                users = [user._asdict() for user in psutil.users()]
        except:
            self.agent_log.error("Could not get users, connected to the system!")
            self.agent_log.stacktrace(traceback.format_exc())

        processes = []
        if self.Config.config.getboolean('default', 'processstats'):
            for pid in psutil.pids():
                try:
                    process = {
                        'pid': pid,
                        'ppid': None,
                        'status': "",
                        'username': "",
                        'nice': None,  # rename later to nice_level for legacy reasons
                        'name': "",
                        'exe': "",  # rename later to exec for legacy reasons
                        'cmdline': "",
                        'cpu_percent': None,
                        'memory_info': {},  # rename later to memory
                        'memory_percent': None,
                        'num_fds': {},
                        'io_counters': {},
                        'open_files': "",
                        'children': []
                    }

                    # Rename the fields to be backwards compatible to version 1.x
                    rename = {
                        'nice': 'nice_level',
                        'exe': 'exec',
                        'memory_info': 'memory'
                    }

                    p = psutil.Process(pid)
                    with p.oneshot():
                        if pid not in (0, 1, 2):
                            try:
                                parent = p.parent()
                                if hasattr(parent, 'pid'):
                                    process['ppid'] = p.parent().pid
                            except:
                                pass

                        if self.Config.config.getboolean('default', 'processstats-including-child-ids', fallback=False):
                            try:
                                with self.suppress_stdout_stderr():
                                    for child in p.children(recursive=True):
                                        process['children'].append(child.pid)
                            except psutil.AccessDenied as e:
                                self.agent_log.psutil_access_denied(
                                    pid=e.pid,
                                    name=e.name,
                                    type="child process IDs"
                                )
                            except:
                                self.agent_log.stacktrace(traceback.format_exc())

                        attributes = ['nice', 'name', 'username', 'exe', 'cmdline', 'cpu_percent', 'memory_info',
                                      'memory_percent', 'num_fds', 'open_files', 'io_counters']
                        for attr in attributes:
                            try:
                                if attr == 'cpu_percent':
                                    process[attr] = p.cpu_percent(interval=None)
                                elif attr == 'memory_info':
                                    process[attr] = p.memory_info()._asdict()
                                elif attr == 'io_counters':
                                    if hasattr(p, 'io_counters'):
                                        process[attr] = p.io_counters.__dict__
                                else:
                                    if hasattr(p, attr):
                                        process[attr] = getattr(p, attr)()
                            except psutil.AccessDenied as e:
                                self.agent_log.psutil_access_denied(
                                    pid=e.pid,
                                    name=e.name,
                                    type=attr
                                )
                            except:
                                self.agent_log.stacktrace(traceback.format_exc())

                    for key_to_rename in rename:
                        rename_to = rename[key_to_rename]

                        value_to_move = process.pop(key_to_rename)
                        process[rename_to] = value_to_move

                    process['name'] = process['name'][:1000]
                    process['exec'] = process['exec'][:1000]
                    process['cmdline'] = process['cmdline'][:1000]

                    processes.append(process)

                except psutil.NoSuchProcess:
                    continue

                except psutil.AccessDenied:
                    continue

                except:
                    self.agent_log.error("An error occurred during process check!")
                    self.agent_log.stacktrace(traceback.format_exc())

        windows_services = []
        windows_eventlog = {}
        if self.operating_system.isWindows() is True:
            if self.Config.config.getboolean('default', 'winservices', fallback=True):
                try:
                    for win_process in psutil.win_service_iter():
                        windows_services.append(win_process.as_dict())
                except:
                    self.agent_log.error("An error occurred during windows services check!")
                    self.agent_log.stacktrace(traceback.format_exc())

            if self.Config.config.getboolean('default', 'wineventlog', fallback=True):
                try:
                    server = 'localhost'  # name of the target computer to get event logs
                    logTypes = []
                    fallback_logtypes = 'System, Application, Security'
                    if self.Config.config.get('default', 'wineventlog-logtypes', fallback=fallback_logtypes) != "":
                        for logtype in self.Config.config.get('default', 'wineventlog-logtypes',
                                                              fallback=fallback_logtypes).split(','):
                            if logtype.strip() != '':
                                logTypes.append(logtype.strip())
                    else:
                        logTypes = ['System', 'Application', 'Security']

                    evt_dict = {
                        win32con.EVENTLOG_AUDIT_FAILURE: 'EVENTLOG_AUDIT_FAILURE',  # 16 -> critical
                        win32con.EVENTLOG_AUDIT_SUCCESS: 'EVENTLOG_AUDIT_SUCCESS',  # 8  -> ok
                        win32con.EVENTLOG_INFORMATION_TYPE: 'EVENTLOG_INFORMATION_TYPE',  # 4  -> ok
                        win32con.EVENTLOG_WARNING_TYPE: 'EVENTLOG_WARNING_TYPE',  # 2  -> warning
                        win32con.EVENTLOG_ERROR_TYPE: 'EVENTLOG_ERROR_TYPE'  # 1  -> critical
                    }

                    for logType in logTypes:
                        try:
                            if logType not in windows_eventlog:
                                windows_eventlog[logType] = []
                            hand = win32evtlog.OpenEventLog(server, logType)
                            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
                            total = win32evtlog.GetNumberOfEventLogRecords(hand)
                            events = win32evtlog.ReadEventLog(hand, flags, 0)
                            if events:
                                for event in events:
                                    msg = win32evtlogutil.SafeFormatMessage(event, logType)
                                    sidDesc = None
                                    if event.Sid is not None:
                                        try:
                                            domain, user, typ = win32security.LookupAccountSid(server, event.Sid)
                                            sidDesc = "%s/%s" % (domain, user)
                                        except win32security.error:
                                            sidDesc = str(event.Sid)

                                    evt_type = "unknown"
                                    if event.EventType in evt_dict.keys():
                                        evt_type = str(evt_dict[event.EventType])

                                    tmp_evt = {
                                        'event_category': event.EventCategory,
                                        'time_generated': str(event.TimeGenerated),
                                        'source_name': event.SourceName,
                                        'associated_user': sidDesc,
                                        'event_id': event.EventID,
                                        'event_type': evt_type,
                                        'event_type_id': event.EventType,
                                        'event_msg': msg,
                                        'event_data': [data for data in
                                                       event.StringInserts] if event.StringInserts else ''
                                    }
                                    windows_eventlog[logType].append(tmp_evt)

                        except Exception as e:
                            self.agent_log.error(
                                "An error occurred during windows eventlog check with log type %s!" % (logType))
                            self.agent_log.error(str(e))
                            self.agent_log.stacktrace(traceback.format_exc())

                except:
                    self.agent_log.error("An error occurred during windows eventlog check!")
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

        out = {
            'agent': agent,
            # 'disks': disks,
            # 'disk_io': diskIO,
            # 'disk_io_total': diskIOTotal,
            # 'net_stats': net_stats,
            # 'net_io': netIO,

            # 'sensors': sensors,

            # 'cpu_total_percentage': cpuTotalPercentage,
            # 'cpu_percentage': cpuPercentage,
            # 'cpu_total_percentage_detailed': cpuTotalPercentageDetailed,
            # 'cpu_percentage_detailed': cpuPercentageDetailed,

            'system_load': system_load_avg,
            'users': users,

            'memory': memory._asdict(),
            'swap': swap._asdict(),
        }

        if self.Config.config.getboolean('default', 'diskstats'):
            out['disks'] = disks

        if self.Config.config.getboolean('default', 'diskio'):
            out['disk_io'] = diskIO

        if self.Config.config.getboolean('default', 'netstats'):
            out['net_stats'] = net_stats

        if self.Config.config.getboolean('default', 'netio'):
            out['net_io'] = netIO

        if self.Config.config.getboolean('default', 'sensorstats'):
            out['sensors'] = sensors

        if self.Config.config.getboolean('default', 'cpustats', fallback=True):
            out['cpu_total_percentage'] = cpuTotalPercentage
            out['cpu_percentage'] = cpuPercentage
            out['cpu_total_percentage_detailed'] = cpuTotalPercentageDetailed
            out['cpu_percentage_detailed'] = cpuPercentageDetailed

        if self.Config.config.getboolean('default', 'processstats'):
            out['processes'] = processes

        if self.operating_system.isWindows() is True:
            if self.Config.config.getboolean('default', 'winservices'):
                out['windows_services'] = windows_services
            if self.Config.config.getboolean('default', 'wineventlog'):
                out['windows_eventlog'] = windows_eventlog

        # if len(systemd_services_data) > 0:
        #    out['systemd_services'] = systemd_services_data
        #
        # if len(cached_customchecks_check_data) > 0:
        #    out['customchecks'] = cached_customchecks_check_data
        #
        # if len(docker_stats_data) > 0:
        #    out['dockerstats'] = docker_stats_data
        #
        # if len(qemu_stats_data) > 0:
        #    out['qemustats'] = qemu_stats_data
        #
        # if 'result' in alfresco_stats_data and config['default']['alfrescostats'] in (1, "1", "true", "True"):
        #    out['alfrescostats'] = alfresco_stats_data['result']

        # if jmx_import_successfull and 'alfrescostats' in config['default'] and config['default']['alfrescostats'] in (1, "1", "true", "True", True):
        #    out['alfrescostats'] = alfrescostats
        # if self.Config.verbose:
        #    print_lock.release()

        return out.copy()

    def wrapdiff(self, last, curr):
        """ Function to calculate the difference between last and curr

            If last > curr, try to guess the boundary at which the value must have wrapped
            by trying the maximum values of 64, 32 and 16 bit signed and unsigned ints.
        """

        if last <= curr:
            return float(curr - last)

        boundary = None
        for chkbound in (64, 63, 32, 31, 16, 15):
            if last > 2 ** chkbound:
                break
            boundary = chkbound
        if boundary is None:
            raise ArithmeticError("Couldn't determine boundary")
        return float(2 ** boundary - last + curr)

    @contextmanager
    def suppress_stdout_stderr(self):
        """A context manager that redirects stdout and stderr to devnull"""
        with open(os.devnull, "w") as devnull:
            old_stdout = sys.stdout
            sys.stdout = devnull
            try:
                yield
            finally:
                sys.stdout = old_stdout
