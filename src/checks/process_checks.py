import os
import sys
import traceback
from contextlib import contextmanager

import psutil

from checks.default_check import DefaultCheck

if sys.platform == 'win32' or sys.platform == 'win64':
    pass


class ProcessChecks(DefaultCheck):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.key_name = "processes"

    def run_check(self):
        self.agent_log.verbose('Running process checks')

        processes = []
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
                                  'memory_percent', 'num_fds', 'io_counters']
                    if not self.operating_system.windows:
                        attributes.append('open_files')

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
                        except OSError:
                            # Mostlikely this is the process "Registry" on Windows
                            # OSError: [WinError 1168] Element nicht gefunden: '(originated from NtQueryInformationProcess(ProcessBasicInformation))'
                            pass
                        except Exception as err:
                            # print(type(err))
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

        return processes

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
