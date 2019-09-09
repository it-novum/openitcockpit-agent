#!/usr/bin/python

# supports python2.7 and python3.7
#
#
# start with parameters:    ./oitc_agent.py -i 30 -p 3333 -a 127.0.0.1
#
# Download & install python
#
# Windows:
#   Download & install current python version from https://www.python.org/downloads/windows/
#   open cmd and execute:   python.exe -m pip install psutil configparser pycryptodome pyopenssl --user
#
# Debian:       
#       python3:
#               apt-get install python3 python3-psutil
#               pip3 uninstall psutil
#               pip3 install configparser pycryptodome pyopenssl
#       or
#       python2:
#               apt-get install python python-psutil
#               pip uninstall psutil
#               pip install configparser futures subprocess32
# Ubuntu:
#       Python 3:
#               apt-get install python3 python3-pip
#               pip3 install configparser psutil pycryptodome pyopenssl
#
# Darwin:
#               brew install python3
#               pip3 install psutil configparser pycryptodome pyopenssl
#



import sys
import os
import io
import getopt
import platform
import datetime
import time
import json
import socket
import configparser
import traceback
import base64
import signal
import OpenSSL
import ssl

from os import access, R_OK, devnull
from os.path import isfile
from time import sleep
from contextlib import contextmanager
from OpenSSL.SSL import FILETYPE_PEM
from OpenSSL.crypto import (dump_certificate_request, dump_privatekey, load_certificate, PKey, TYPE_RSA, X509Req)

isPython3 = False
system = 'linux'
    
if sys.platform == 'darwin' or (system == 'linux' and 'linux' not in sys.platform):
    system = 'darwin'

if (sys.version_info > (3, 0)):
    isPython3 = True
    import concurrent.futures as futures
    import urllib.request, urllib.parse
    import subprocess
    
    from _thread import start_new_thread as permanent_check_thread
    from _thread import start_new_thread as permanent_webserver_thread
    from _thread import start_new_thread as oitc_notification_thread
    from _thread import start_new_thread as permanent_customchecks_check_thread
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from subprocess import Popen, PIPE
else:
    print('#########################################################')
    print('#             !!!   Python 2 Warning   !!!              #')
    print('#                                                       #')
    print('# Python 2 is End Of Life and will not be maintained    #')
    print('# past  January 1, 2020!                                #')
    print('# https://www.python.org/dev/peps/pep-0373/             #')
    print('#                                                       #')
    print('# Update your system to Python 3!                       #')
    print('#########################################################')
    print('')
    
    import urllib
    import urllib2
    import subprocess32 as subprocess
    
    from concurrent import futures
    from thread import start_new_thread as permanent_check_thread
    from thread import start_new_thread as permanent_webserver_thread
    from thread import start_new_thread as oitc_notification_thread
    from thread import start_new_thread as permanent_customchecks_check_thread
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    
try:
    import psutil
    if isPython3 and psutil.version_info < (5, 5, 0):
        print('psutil >= 5.5.0 required!')
        raise ImportError('psutil version too old!')
        
except ImportError:
    if system is 'windows':
        print('Install Python psutil: python.exe -m pip install psutil')
    elif system is 'linux' and isPython3:
        print('Install Python psutil: pip3 uninstall psutil && apt-get install python3-psutil')
    elif system is 'linux' and not isPython3:
        print('Install Python psutil: pip uninstall psutil && apt-get install python-psutil')
    else:
        print('Install Python psutil: pip install psutil')
    sys.exit(1)

def signal_handler(sig, frame):
    global thread_stop_requested
    global webserver_stop_requested
    global wait_and_check_auto_certificate_thread_stop_requested
    
    thread_stop_requested = True
    webserver_stop_requested = True
    wait_and_check_auto_certificate_thread_stop_requested = True
    if verbose:
        print("... see you ...\n")
    sys.exit(0)

agentVersion = "1.0.0"
enableSSL = False
autossl = True
cached_check_data = {}
cached_customchecks_check_data = {}
cached_diskIO = {}
cached_netIO = {}
configpath = ""
verbose = False
stacktrace = False
added_oitc_parameter = 0
temperatureIsFahrenheit = False
initialized = False

thread_stop_requested = False
webserver_stop_requested = False
wait_and_check_auto_certificate_thread_stop_requested = False

permanent_check_thread_running = False
permanent_webserver_thread_running = False
oitc_notification_thread_running = False
permanent_customchecks_check_thread_running = False

etc_agent_path = '/etc/openitcockpit-agent/'
if system is 'windows':
    etc_agent_path = 'C:'+os.path.sep+'Program Files'+os.path.sep+'openitcockpit-agent'+os.path.sep

default_ssl_csr_file = etc_agent_path + 'agent.csr'
default_ssl_crt_file = etc_agent_path + 'agent.crt'
default_ssl_key_file = etc_agent_path + 'agent.key'
default_ssl_ca_file = etc_agent_path + 'server_ca.crt'

ssl_csr = None
agent_id = 'XXX089zugbhnjk'


sample_config = """
[default]
  interval = 30
  port = 3333
  address = 127.0.0.1
  certfile = 
  keyfile = 
  try-autossl = true
  autossl-csr-file = 
  autossl-crt-file = 
  autossl-key-file = 
  autossl-ca-file = 
  verbose = false
  stacktrace = false
  config-update-mode = false
  auth = 
  customchecks = 
  temperature-fahrenheit = false
[oitc]
  hostuuid = 
  url = 
  apikey = 
  interval = 60
  enabled = false
"""

sample_customcheck_config = """
[default]
  # max_worker_threads should be increased with increasing number of custom checks
  # but consider: each thread needs (a bit) memory
  max_worker_threads = 4
[username]
  command = whoami
  interval = 30
  timeout = 5
  enabled = false
[uname]
  command = uname -a
  interval = 15
  timeout = 5
  enabled = false
"""

config = configparser.ConfigParser(allow_no_value=True)
customchecks = configparser.ConfigParser(allow_no_value=True)

def reset_global_options():
    globals()['enableSSL'] = False
    globals()['cached_check_data'] = {}
    globals()['cached_customchecks_check_data'] = {}
    globals()['configpath'] = ""
    globals()['verbose'] = False
    globals()['stacktrace'] = False
    globals()['added_oitc_parameter'] = 0
    globals()['initialized'] = False
    globals()['thread_stop_requested'] = False
    globals()['permanent_check_thread_running'] = False
    globals()['permanent_webserver_thread_running'] = False
    globals()['oitc_notification_thread_running'] = False
    globals()['permanent_customchecks_check_thread_running'] = False
    globals()['config'] = configparser.ConfigParser(allow_no_value=True)
    globals()['customchecks'] = configparser.ConfigParser(allow_no_value=True)


@contextmanager
def suppress_stdout_stderr():
    """A context manager that redirects stdout and stderr to devnull"""
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:  
            yield
        finally:
            sys.stdout = old_stdout

def wrapdiff(last, curr):
    """ Calculate the difference between last and curr.
        If last > curr, try to guess the boundary at which the value must have wrapped
        by trying the maximum values of 64, 32 and 16 bit signed and unsigned ints.
    """
    
    if last <= curr:
        return float(curr - last)

    boundary = None
    for chkbound in (64,63,32,31,16,15):
        if last > 2**chkbound:
            break
        boundary = chkbound
    if boundary is None:
        raise ArithmeticError("Couldn't determine boundary")
    return float(2**boundary - last + curr)

class Collect:
    def getData(self):
        global cached_diskIO
        global cached_netIO
        
        # CPU #
        cpuTotalPercentage = psutil.cpu_percent()
        cpuPercentage = psutil.cpu_percent(interval=0, percpu=True)

        cpu = psutil.cpu_times_percent(interval=0, percpu=False)
        cpuTotalPercentageDetailed = cpu._asdict()
        
        cpuPercentageDetailed = [dict(cpu._asdict()) for cpu in psutil.cpu_times_percent(interval=0, percpu=True)]
        
        uptime = 0
        try:
            if hasattr(psutil, "boot_time") and callable(psutil.boot_time):
                uptime = int(time.time() - psutil.boot_time())
            else:
                uptime = int(time.time() - psutil.BOOT_TIME)
        except:
            if stacktrace:
                traceback.print_exc()
            if verbose:
                print ("Could not get system uptime!")

        #totalCpus = psutil.cpu_count()
        #physicalCpus = psutil.cpu_count(logical=False)

        #cpuFrequency = psutil.cpu_freq()

        # MEMORY #

        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # DISKS #        
        disks = [dict(
            disk = disk._asdict(),
            usage = psutil.disk_usage(disk.mountpoint)._asdict()
            ) for disk in psutil.disk_partitions() ]
       

        #diskIOTotal = psutil.disk_io_counters(perdisk=False)._asdict()
        
        diskIO = None
        if hasattr(psutil, "disk_io_counters"):
            #diskIO = psutil.disk_io_counters(perdisk=True)
            diskIO = { disk: iops._asdict() for disk,iops in psutil.disk_io_counters(perdisk=True).items() }
            diskIO['timestamp'] = time.time()
            
            for disk in diskIO:
                if disk != "timestamp" and disk in cached_diskIO:
                    
                    diskIODiff = {}
                    diskIODiff['timestamp'] = wrapdiff(float(cached_diskIO['timestamp']), float(diskIO['timestamp']))
                    
                    for attr in diskIO[disk]:
                        diff = wrapdiff(float(cached_diskIO[disk][attr]), float(diskIO[disk][attr]))
                        diskIODiff[attr] = diff;
                    
                    diskIO[disk]['read_iops'] = diskIODiff['read_count'] / diskIODiff['timestamp']
                    diskIO[disk]['write_iops'] = diskIODiff['write_count'] / diskIODiff['timestamp']
                    
                    tot_ios = diskIODiff['read_count'] + diskIODiff['write_count']
                    diskIO[disk]['total_iops'] = tot_ios / diskIODiff['timestamp']
                    #diskIO[disk]['tot_ticks'] = diskIODiff['busy_time']
                    #diskIO[disk]['interval'] = diskIODiff['timestamp']
                    if 'busy_time' in diskIODiff:
                        diskIO[disk]['load_percent'] = diskIODiff['busy_time'] / (diskIODiff['timestamp'] * 1000.) * 100.
                    
                    if diskIODiff['read_count']:
                        diskIO[disk]['read_avg_wait'] = float(diskIODiff['read_time'] / diskIODiff['read_count'])
                        diskIO[disk]['read_avg_size'] = float(diskIODiff['read_bytes'] / diskIODiff['read_count'])
                    else:
                        diskIO[disk]['read_avg_wait'] = 0
                        diskIO[disk]['read_avg_size'] = 0
                        
                    if diskIODiff['write_count']:
                        diskIO[disk]['write_avg_wait'] = float(diskIODiff['write_time'] / diskIODiff['write_count'])
                        diskIO[disk]['write_avg_size'] = float(diskIODiff['write_bytes'] / diskIODiff['write_count'])
                    else:
                        diskIO[disk]['write_avg_wait'] = 0
                        diskIO[disk]['write_avg_size'] = 0
                    
                    if tot_ios:
                        diskIO[disk]['total_avg_wait'] = float((diskIODiff['read_time'] + diskIODiff['write_time']) / tot_ios)
                    else:
                        diskIO[disk]['total_avg_wait'] = 0
            
            cached_diskIO = diskIO
        
        netIO = None
        if hasattr(psutil, "net_io_counters"):
            netIO = { device: data._asdict() for device,data in psutil.net_io_counters(pernic=True).items() }
            netIO['timestamp'] = time.time()
            
            for device in netIO:
                if device != "timestamp" and device in cached_netIO:
                    
                    netIODiff = {}
                    netIODiff['timestamp'] = wrapdiff(float(cached_netIO['timestamp']), float(netIO['timestamp']))
                    
                    for attr in netIO[device]:
                        diff = wrapdiff(float(cached_netIO[device][attr]), float(netIO[device][attr]))
                        netIODiff[attr] = diff;
                        
                    if netIODiff['bytes_sent']:
                        netIO[device]['avg_bytes_sent_ps'] = float(netIODiff['bytes_sent'] / netIODiff['timestamp'])
                    else:
                        netIO[device]['avg_bytes_sent_ps'] = 0
                    
                    if netIODiff['bytes_recv']:
                        netIO[device]['avg_bytes_recv_ps'] = float(netIODiff['bytes_recv'] / netIODiff['timestamp'])
                    else:
                        netIO[device]['avg_bytes_recv_ps'] = 0
                        
                    if netIODiff['packets_sent']:
                        netIO[device]['avg_packets_sent_ps'] = float(netIODiff['packets_sent'] / netIODiff['timestamp'])
                    else:
                        netIO[device]['avg_packets_sent_ps'] = 0
                    
                    if netIODiff['packets_recv']:
                        netIO[device]['avg_packets_recv_ps'] = float(netIODiff['packets_recv'] / netIODiff['timestamp'])
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
                    
                
            cached_netIO = netIO
        
        net_stats = None
        if hasattr(psutil, "net_if_stats"):
            net_stats = { device: data._asdict() for device,data in psutil.net_if_stats().items() }

        sensors = {}
        try:
            if hasattr(psutil, "sensors_temperatures"):
                sensors['temperatures'] = {}
                for device,data in psutil.sensors_temperatures(fahrenheit=temperatureIsFahrenheit).items():
                    sensors['temperatures'][device] = []
                    for value in data:
                        sensors['temperatures'][device].append(value._asdict())
            else:
                sensors['temperatures'] = {}
        except:
            if stacktrace:
                traceback.print_exc()
            if verbose:
                print ("Could not get temperature sensor data!")
        
        try:
            if hasattr(psutil, "sensors_fans"):
                sensors['fans'] = {}
                for device,data in psutil.sensors_fans().items():
                    sensors['fans'][device] = []
                    for value in data:
                        sensors['fans'][device].append(value._asdict())
            else:
                sensors['fans'] = {}
        except:
            if stacktrace:
                traceback.print_exc()
            if verbose:
                print ("Could not get fans sensor data!")
        
        try:
            if hasattr(psutil, "sensors_battery"):
                sensors['battery'] = psutil.sensors_battery()._asdict()
            else:
                sensors['battery'] = {}
        except:
            if stacktrace:
                traceback.print_exc()
            if verbose:
                print ("Could not get battery sensor data!")
        
        if hasattr(psutil, "pids"):
            pids = psutil.pids()
        else:
            pids = psutil.get_pid_list()
        
        system_load_avg = []
        try:
            if hasattr(psutil, "getloadavg"):
                system_load_avg = psutil.getloadavg()
        except:
            if stacktrace:
                traceback.print_exc()
            if verbose:
                print ("Could not get average system load!")
                
        users = []
        try:
            if hasattr(psutil, "users"):
                users = [ user._asdict() for user in psutil.users() ]
        except:
            if stacktrace:
                traceback.print_exc()
            if verbose:
                print ("Could not get users, connected to the system!")

        #processes = [ psutil.Process(pid).as_dict() for pid in pids ]
        windows_services = []
        processes = []
        customchecks = {}
        
        tmpProcessList = []
        
        
        for pid in pids:
            try:
                p = psutil.Process(pid)
                
                try:
                    if hasattr(p, "cpu_percent") and callable(p.cpu_percent):
                        cpu_percent = p.cpu_percent(interval=None)
                    else:
                        cpu_percent = p.get_cpu_percent(interval=None)
                        
                    tmpProcessList.append(p)
                except:
                    if stacktrace:
                        traceback.print_exc()
                    if verbose:
                        print ("'%s' Process is not allowing us to get the CPU usage!" % (name if name != "" else str(pid)))
            
            except psutil.NoSuchProcess:
                continue;
            except:
                if stacktrace:
                    traceback.print_exc()
                if verbose:
                    print ("An error occured during process check! Enable --stacktrace to get more information.")
        
        for p in tmpProcessList:
            try:
                
                pid = p.pid
                ppid = None
                status = ""
                username = ""
                nice = None
                name = ""
                exe = ""
                cmdline = ""
                cpu_percent = None
                memory_info = {}
                memory_percent = None
                num_fds = {}
                io_counters = {}
                open_files = ""
                children = []
                
                
                if pid not in (1, 2):
                    try:
                        if callable(p.parent):
                            ppid = p.parent().pid
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except AttributeError:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the parent process id!" % (str(pid)))
                    
                    try:
                        if callable(p.children):
                            with suppress_stdout_stderr():
                                for child in p.children(recursive=True):
                                    children.append(child.pid)
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the child process ids!" % (str(pid)))
                
                
                if isPython3:
                    try:
                        nice = p.nice()
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the nice option!" % (name if name != "" else str(pid)))
                
                    try:
                        name = p.name()
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the name option!" % (name if name != "" else str(pid)))
                
                    try:
                        exe = p.exe()
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the exec option!" % (name if name != "" else str(pid)))
                    
                    try:
                        cmdline = p.cmdline()
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the cmdline option!" % (name if name != "" else str(pid)))
                    
                    try:
                        cpu_percent = p.cpu_percent(interval=None)
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the CPU usage!" % (name if name != "" else str(pid)))
                    
                    try:
                        memory_info = p.memory_info()._asdict()
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get memory usage information!" % (name if name != "" else str(pid)))
                    
                    try:
                        memory_percent = p.memory_percent()
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the percent of memory usage!" % (name if name != "" else str(pid)))
                    
                    try:
                        num_fds = p.num_fds()
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the num_fds option!" % (name if name != "" else str(pid)))
                    
                    try:
                        io_counters = p.io_counters.__dict__
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the IO counters!" % (name if name != "" else str(pid)))
                    
                    try:
                        open_files = p.open_files()
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except psutil.AccessDenied:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the open_files option!" % (name if name != "" else str(pid)))
                
                
                if not isPython3:
                    try:
                        nice = p.nice
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the nice option!" % (name if name != "" else str(pid)))
                    
                    try:
                        name = p.name
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the name option!" % (name if name != "" else str(pid)))
                    
                    try:
                        exe = p.exe
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the exec option!" % (name if name != "" else str(pid)))
                        
                    try:
                        cmdline = p.cmdline
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the cmdline option!" % (name if name != "" else str(pid)))
                    
                    try:
                        cpu_percent = p.get_cpu_percent(interval=None)
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the CPU usage!" % (name if name != "" else str(pid)))
                        
                    try:
                        memory_info = p.get_memory_info()._asdict()
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get memory usage information!" % (name if name != "" else str(pid)))
                    
                    try:
                        memory_percent = p.get_memory_percent()
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the percent of memory usage!" % (name if name != "" else str(pid)))

                    try:
                        num_fds = p.get_num_fds()
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the num_fds option!" % (name if name != "" else str(pid)))
                
                    try:
                        io_counters = p.get_io_counters().__dict__
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the IO counters!" % (name if name != "" else str(pid)))
                
                    try:
                        open_files = p.get_open_files()
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        continue;
                    except psutil.AccessDenied:
                        if stacktrace:
                            traceback.print_exc()
                        if verbose:
                            print ("'%s' Process is not allowing us to get the open_files option!" % (name if name != "" else str(pid)))
                    
                    
                process = {
                    'name': name,
                    'exec': exe,
                    'cmdline': cmdline,
                    'pid': pid,
                    'ppid': ppid,
                    'children': children,
                    'status': status,
                    'username': username,
                    'cpu_percent': cpu_percent,
                    'memory': memory_info,
                    'memory_percent': memory_percent,
                    'num_fds': num_fds,
                    'open_files': open_files,
                    'io_counters': io_counters,
                    'nice_level': nice
                }
                processes.append(process)
            except psutil.NoSuchProcess:
                continue;
            except:
                if stacktrace:
                    traceback.print_exc()
                if verbose:
                    print ("An error occured during process check! Enable --stacktrace to get more information.")
        
        if system is 'windows':
            for win_process in psutil.win_service_iter():
                windows_services.append(win_process.as_dict())
                
        try:
            agent = {
                'last_updated': time.ctime(),
                'last_updated_timestamp': round(time.time()),
                'system': platform.system(),
                'system_uptime': uptime,
                'kernel_version': platform.release(),
                'mac_version': platform.mac_ver()[0],
                'agent_version': agentVersion,
                'temperature_unit': 'F' if temperatureIsFahrenheit else 'C'
            }
        except:
            agent = {
                'last_updated': time.ctime(),
                'last_updated_timestamp': round(time.time()),
                'system_uptime': uptime,
                'agent_version': agentVersion,
                'temperature_unit': 'F' if temperatureIsFahrenheit else 'C'
            }

        out = {
            'disks': disks,
            'disk_io': diskIO,
            #'disk_io_total': diskIOTotal,
            'net_io': netIO,
            'net_stats': net_stats,
            
            'sensors': sensors,
    
            'cpu_total_percentage': cpuTotalPercentage,
            'cpu_percentage': cpuPercentage,
            'cpu_total_percentage_detailed': cpuTotalPercentageDetailed,
            'cpu_percentage_detailed': cpuPercentageDetailed,
            
            'system_load': system_load_avg,
            'users': users,
            
            'memory': memory._asdict(),
            'swap': swap._asdict(),
    
            'processes': processes,
            'agent': agent
        }
        
        if system is 'windows':
            out['windows_services'] = windows_services;
            
        if len(cached_customchecks_check_data) > 0:
            out['customchecks'] = cached_customchecks_check_data;
        
        return out

def file_readable(path):
    return (isfile(path) and access(path, R_OK))

def isBase64(s):
    try:
        return base64.b64encode(base64.b64decode(s)) == s
    except Exception:
        return False

def check_update_crt(data):
    try:
        jdata = json.loads(data.decode('utf-8'))
        if 'signed' in jdata and 'ca' in jdata:
            with open(config['default']['autossl-crt-file'], 'w+') as f:
                f.write(jdata['signed'])
            with open(config['default']['autossl-ca-file'], 'w+') as f:
                f.write(jdata['ca'])
            
            return True
        
    except Exception as e:
        if stacktrace:
            traceback.print_exc
            print(e)
        elif verbose:
            print('an error occured during new crt processing')
        
def check_update_data(data):
    try:
        jdata = json.loads(data.decode('utf-8'))

        for key in jdata:
            if key == 'config' and file_readable(configpath):
                newconfig = configparser.ConfigParser(allow_no_value=True)
                newconfig['default'] = {}
                newconfig['oitc'] = {}
                
                if 'interval' in jdata[key]:
                    if int(jdata[key]['interval']) > 0:
                        newconfig['default']['interval'] = str(jdata[key]['interval'])
                if 'port' in jdata[key]:
                    if int(jdata[key]['port']) > 0:
                        newconfig['default']['port'] = str(jdata[key]['port'])
                if 'address' in jdata[key]:
                    newconfig['default']['address'] = str(jdata[key]['address'])
                if 'certfile' in jdata[key]:
                    newconfig['default']['certfile'] = str(jdata[key]['certfile'])
                if 'keyfile' in jdata[key]:
                    newconfig['default']['keyfile'] = str(jdata[key]['keyfile'])
                if 'try-autossl' in jdata[key]:
                    if jdata[key]['try-autossl'] in (1, "1", "true", "True"):
                        newconfig['default']['try-autossl'] = "true"
                    else:
                        newconfig['default']['try-autossl'] = "false"
                if 'auth' in jdata[key]:
                    newconfig['default']['auth'] = str(jdata[key]['auth'])
                if 'verbose' in jdata[key]:
                    if jdata[key]['verbose'] in (1, "1", "true", "True"):
                        newconfig['default']['verbose'] = "true"
                    else:
                        newconfig['default']['verbose'] = "false"
                if 'stacktrace' in jdata[key]:
                    if jdata[key]['stacktrace'] in (1, "1", "true", "True"):
                        newconfig['default']['stacktrace'] = "true"
                    else:
                        newconfig['default']['stacktrace'] = "false"
                if 'config-update-mode' in jdata[key]:
                    if jdata[key]['config-update-mode'] in (1, "1", "true", "True"):
                        newconfig['default']['config-update-mode'] = "true"
                    else:
                        newconfig['default']['config-update-mode'] = "false"
                if 'customchecks' in jdata[key]:
                    newconfig['default']['customchecks'] = str(jdata[key]['customchecks'])
                if 'temperature-fahrenheit' in jdata[key]:
                    if jdata[key]['temperature-fahrenheit'] in (1, "1", "true", "True"):
                        newconfig['default']['temperature-fahrenheit'] = "true"
                    else:
                        newconfig['default']['temperature-fahrenheit'] = "false"
                if 'oitc-hostuuid' in jdata[key]:
                    newconfig['oitc']['hostuuid'] = str(jdata[key]['oitc-hostuuid'])
                if 'oitc-url' in jdata[key]:
                    newconfig['oitc']['url'] = str(jdata[key]['oitc-url'])
                if 'oitc-apikey' in jdata[key]:
                    newconfig['oitc']['apikey'] = str(jdata[key]['oitc-apikey'])
                if 'oitc-interval' in jdata[key]:
                    newconfig['oitc']['interval'] = str(jdata[key]['oitc-interval'])
                if 'oitc-enabled' in jdata[key]:
                    if jdata[key]['oitc-enabled'] in (1, "1", "true", "True"):
                        newconfig['oitc']['enabled'] = "true"
                    else:
                        newconfig['oitc']['enabled'] = "false"
                        
                if configpath != "":
                    with open(configpath, 'w') as configfile:
                        if verbose:
                            print('update agent configuration')
                        newconfig.write(configfile)
                else:
                    if verbose:
                        print('no valid configpath')
            elif key == 'config' and not file_readable(configpath):
                if verbose:
                    print('agent configuration file not readable')
            
            if key == 'customchecks' and file_readable(config['default']['customchecks']):
                newcustomchecks = configparser.ConfigParser(allow_no_value=True)
                if isPython3:
                    newcustomchecks.read_string(sample_customcheck_config)
                else:
                    newcustomchecks.readfp(io.BytesIO(sample_customcheck_config))
                
                for customkey in jdata[key]:
                    newcustomchecks[customkey] = {}
                    
                    if customkey == 'default':
                        if 'max_worker_threads' in jdata[key][customkey]:
                            newcustomchecks[customkey]['max_worker_threads'] = str(jdata[key][customkey]['max_worker_threads'])
                    else:
                    
                        if 'command' in jdata[key][customkey]:
                            newcustomchecks[customkey]['command'] = str(jdata[key][customkey]['command'])
                        if 'interval' in jdata[key][customkey]:
                            if int(jdata[key][customkey]['interval']) > 0:
                                newcustomchecks[customkey]['interval'] = str(jdata[key][customkey]['interval'])
                        if 'timeout' in jdata[key][customkey]:
                            if int(jdata[key][customkey]['timeout']) > 0:
                                newcustomchecks[customkey]['timeout'] = str(jdata[key][customkey]['timeout'])
                        if 'enabled' in jdata[key][customkey]:
                            newcustomchecks[customkey]['enabled'] = "false"
                            if jdata[key][customkey]['enabled'] in (1, "1", "true", "True"):
                                newcustomchecks[customkey]['enabled'] = "true"
                            
                if config['default']['customchecks'] != "":
                    with open(config['default']['customchecks'], 'w') as configfile:
                        if verbose:
                            print('update customchecks configuration')
                        newcustomchecks.write(configfile)
                else:
                    if verbose:
                        print('no valid customchecks configpath')
            elif key == 'customchecks' and not file_readable(config['default']['customchecks']):
                if verbose:
                    print('customchecks configuration file not readable')
            
        load_main_processing()
        
    except Exception as e:
        if stacktrace:
            traceback.print_exc
            print(e)
        elif verbose:
            print('an error occured during new config processing')
    
class MyServer(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
    
    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=')
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
    def get_csr(self):
        return create_new_csr(agent_id)
    
    def build_json_config(self):
        data = {}
        data['config'] = {}
        data['customchecks'] = {}
        
        for key in config['default']:
            data['config'][key] = config['default'][key]
        for key in config['oitc']:
            data['config']['oitc-'+key] = config['oitc'][key]
        
        for customkey in customchecks:
            data['customchecks'][customkey] = {}
            if customkey == 'default':
                data['customchecks'][customkey]['max_worker_threads'] = customchecks[customkey]['max_worker_threads']
            else:
                for customkeyoption in customchecks[customkey]:
                    data['customchecks'][customkey][customkeyoption] = customchecks[customkey][customkeyoption]
        
        if 'DEFAULT' in data['customchecks']:
            del data['customchecks']['DEFAULT']
            
        if data['config']['auth'] != "":
            data['config']['auth'] = str(base64.b64decode(data['config']['auth']), "utf-8")
        
        return data
    
    def _process_get_data(self):
        self._set_headers()
        
        if self.path == "/":
            self.wfile.write(json.dumps(cached_check_data).encode())
        elif self.path == "/config" and config['default']['config-update-mode'] in (1, "1", "true", "True", True):
            self.wfile.write(json.dumps(self.build_json_config()).encode())
        elif self.path == "/getCsr":
            data = {}
            if autossl:
                data['csr'] = self.get_csr().decode("utf-8")
            else:
                data['csr'] = "disabled"
            self.wfile.write(json.dumps(data).encode())
        
    
    def do_GET(self):
        try:
            if 'auth' in config['default']:
                if str(config['default']['auth']).strip() and self.headers.get('Authorization') == None:
                    self.do_AUTHHEAD()
                    self.wfile.write('no auth header received'.encode())
                elif self.headers.get('Authorization') == 'Basic ' + config['default']['auth'] or config['default']['auth'] == "":
                    self._process_get_data()
                elif str(config['default']['auth']).strip():
                    self.do_AUTHHEAD()
                    self.wfile.write(self.headers.get('Authorization').encode())
                    self.wfile.write('not authenticated'.encode())
            else:
                self._process_get_data()
        except:
            if stacktrace:
                traceback.print_exc
                
    def _process_post_data(self, data):
        executor = futures.ThreadPoolExecutor(max_workers=1)
        success = {}
        success['success'] = True
        successFalse = {}
        successFalse['success'] = False
        
        if self.path == "/config" and config['default']['config-update-mode'] in (1, "1", "true", "True", True):
            executor.submit(check_update_data, data)
            return success
        elif self.path == "/updateCrt":
            if check_update_crt(data) == True:
                executor.submit(restart_webserver)
                return success
        
        return successFalse
    
    def do_POST(self):
        try:
            if 'auth' in config['default']:
                if str(config['default']['auth']).strip() and self.headers.get('Authorization') == None:
                    self.do_AUTHHEAD()
                    self.wfile.write('no auth header received'.encode())
                elif self.headers.get('Authorization') == 'Basic ' + config['default']['auth'] or config['default']['auth'] == "":
                    self.wfile.write(json.dumps(self._process_post_data(data=self.rfile.read(int(self.headers['Content-Length'])))).encode())
                elif str(config['default']['auth']).strip():
                    self.do_AUTHHEAD()
                    self.wfile.write(self.headers.get('Authorization').encode())
                    self.wfile.write('not authenticated'.encode())
            else:
                retrn = self._process_post_data(data=self.rfile.read(int(self.headers['Content-Length'])))
                print(retrn)
                self.wfile.write(json.dumps(retrn).encode())
        except:
            traceback.print_exc
            print('caught something in do_POST')

    def log_message(self, format, *args):
        if verbose:
            print("%s - - [%s] %s" % (self.address_string(),self.log_date_time_string(),format%args))
        return
    
    

def collect_data_for_cache(check_interval):
    global permanent_check_thread_running
    global cached_check_data

    permanent_check_thread_running = True
    
    time.sleep(1)
    if check_interval <= 0:
        check_interval = 5
    i = check_interval
    while not thread_stop_requested:
        if i >= check_interval:
            cached_check_data = Collect().getData()
            i = 0
        time.sleep(1)
        i += 1
    
    permanent_check_thread_running = False
    if verbose:
        print('stopped permanent_check_thread')

def run_customcheck_command(check):
    if verbose:
        print('start custom check "%s" with timeout %s at %s' % (str(check['name']), str(check['timeout']), str(round(time.time()))))
    cached_customchecks_check_data[check['name']]['running'] = "true";
    cached_customchecks_check_data[check['name']]['command'] = check['command']
    
    try:
        p = subprocess.Popen(check['command'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        try:
            stdout, stderr = p.communicate(timeout=int(check['timeout']))
            p.poll()
            if stdout:
                stdout = stdout.decode()
            if stderr:
                stderr = stderr.decode()
            cached_customchecks_check_data[check['name']]['result'] = str(stdout)
            cached_customchecks_check_data[check['name']]['error'] = None if str(stderr) == 'None' else str(stderr)
            cached_customchecks_check_data[check['name']]['returncode'] = p.returncode
        except subprocess.TimeoutExpired:
            if verbose:
                print('custom check "%s" timed out' % (check['name']))
            p.kill()    #not needed; just to be sure
            cached_customchecks_check_data[check['name']]['result'] = None
            cached_customchecks_check_data[check['name']]['error'] = 'Command timeout after ' + str(check['timeout']) + ' seconds'
            cached_customchecks_check_data[check['name']]['returncode'] = 124
    
    except:
        if stacktrace:
            traceback.print_exc()
        if verbose:
            print ('An error occured while running the custom check "%s"! Enable --stacktrace to get more information.' % (check['name']))
    
    cached_customchecks_check_data[check['name']]['last_updated_timestamp'] = round(time.time())
    cached_customchecks_check_data[check['name']]['last_updated'] = time.ctime()
    del cached_customchecks_check_data[check['name']]['running']
    return True

# wait for thread and delete 'running' option if thread had errors and does not return True
def process_customcheck_results(future_checks):
    for future in futures.as_completed(future_checks):   #, timeout=10
        check = future_checks[future]
        try:
            if not future.result(): #if run_customcheck_command do not return True (exception/error)
                del cached_customchecks_check_data[check['name']]['running']
            if verbose:
                print('custom check "%s" stopped' % (check['name']))
        except:
            if stacktrace:
                traceback.print_exc()
            if verbose:
                print ('An error occured while checking custom check "%s" alive! Enable --stacktrace to get more information.' % (check['name']))
    
    if len(cached_customchecks_check_data) > 0:
        cached_check_data['customchecks'] = cached_customchecks_check_data;

def collect_customchecks_data_for_cache(customchecks):
    global permanent_customchecks_check_thread_running
    permanent_customchecks_check_thread_running = True
    max_workers = 4
    if 'DEFAULT' in customchecks:
        if 'max_worker_threads' in customchecks['DEFAULT']:
            max_workers = int(customchecks['DEFAULT']['max_worker_threads'])
    if 'default' in customchecks:
        if 'max_worker_threads' in customchecks['default']:
            max_workers = int(customchecks['default']['max_worker_threads'])
            
    if verbose:
        print('Start thread pool with max. %s workers' % (str(max_workers)))
    
    executor = futures.ThreadPoolExecutor(max_workers=max_workers)
    
    while not thread_stop_requested:
        need_to_be_checked = []
        for check_name in customchecks:
            if check_name is not 'DEFAULT' and check_name is not 'default':
                if 'command' in customchecks[check_name] and customchecks[check_name]['command'] != '' and ('enabled' not in customchecks[check_name] or customchecks[check_name]['enabled'] in (1, "1", "true", "True", True)):
                    command = customchecks[check_name]['command']
                    interval = int(config['default']['interval'])
                    timeout = 60
                    
                    if customchecks[check_name]['interval']:
                        interval = int(customchecks[check_name]['interval'])
                    if customchecks[check_name]['timeout']:
                        timeout = int(customchecks[check_name]['timeout'])
                    
                    # wenn noch nicht ausgefuehrt erstelle Timestamp = 0
                    if check_name not in cached_customchecks_check_data:
                        cached_customchecks_check_data[check_name] = {
                            'last_updated': time.ctime(0),
                            'last_updated_timestamp': 0
                        }
                    
                    # ausfuehren wenn Differenz von Timestamp des letzten run und jetzt groesser gleich interval
                    if (round(time.time()) - cached_customchecks_check_data[check_name]['last_updated_timestamp']) >= interval and 'running' not in cached_customchecks_check_data[check_name]:
                        check = {
                            'name': check_name,
                            'command': command,
                            'timeout': timeout
                        }
                        need_to_be_checked.append(check)
                        #executor.submit(run_customcheck_command, check)
        
        # Start the load operations and mark each future with its URL
        if len(need_to_be_checked) > 0:
            future_checks = {
                executor.submit(run_customcheck_command, check): check for check in need_to_be_checked
            }
            executor.submit(process_customcheck_results, future_checks) #, timeout=biggestTimeout
        
        time.sleep(1)
    permanent_customchecks_check_thread_running = False
    if verbose:
        print('stopped permanent_customchecks_check_thread')

def notify_oitc(oitc):
    global oitc_notification_thread_running
    global cached_check_data
    
    time.sleep(1)
    if oitc['url'].strip() and oitc['apikey'].strip() and int(oitc['interval']):
        oitc_notification_thread_running = True
        noty_interval = int(oitc['interval'])
        if noty_interval <= 0:
            noty_interval = 5
        while not thread_stop_requested:
            time.sleep(noty_interval)
            if len(cached_check_data) > 0:
                try:
                    if isPython3:
                        data = bytes(urllib.parse.urlencode({'checkdata': cached_check_data, 'hostuuid': oitc['hostuuid']}).encode())
                        req = urllib.request.Request(oitc['url'].strip())
                        req.add_header('Authorization', 'X-OITC-API '+oitc['apikey'].strip())
                        handler = urllib.request.urlopen(req, data)
                        if verbose:
                            print(handler.read().decode('utf-8'))
                    else:
                        data = bytes(urllib.urlencode({'checkdata': cached_check_data, 'hostuuid': oitc['hostuuid']}).encode())
                        req = urllib2.Request(oitc['url'].strip())
                        req.add_header('Authorization', 'X-OITC-API '+oitc['apikey'].strip())
                        handler = urllib2.urlopen(req, data)
                        if verbose:
                            print(handler.read().decode('utf-8'))
                except:
                    if stacktrace:
                        traceback.print_exc()
                    if verbose:
                        print ('An error occured while trying to notify your configured openITCOCKPIT instance! Enable --stacktrace to get more information.')
    oitc_notification_thread_running = False
    if verbose:
        print('stopped oitc_notification_thread')

def process_webserver(enableSSL=False):
    global permanent_webserver_thread_running
    permanent_webserver_thread_running = True
    
    protocol = 'http'
    if config['default']['address'] == "":
        config['default']['address'] = "127.0.0.1"
        
    server_address = ('', int(config['default']['port']))
    httpd = HTTPServer(server_address, MyServer)
    
    if enableSSL:
        import ssl
        protocol = 'https'
        httpd.socket = ssl.wrap_socket(httpd.socket, keyfile=config['default']['keyfile'], certfile=config['default']['certfile'], server_side=True)
    elif autossl and file_readable(config['default']['autossl-key-file']) and file_readable(config['default']['autossl-crt-file']) and file_readable(config['default']['autossl-ca-file']):
        import ssl
        protocol = 'https'
        httpd.socket = ssl.wrap_socket(httpd.socket, keyfile=config['default']['autossl-key-file'], certfile=config['default']['autossl-crt-file'], server_side=True, cert_reqs = ssl.CERT_REQUIRED, ca_certs = config['default']['autossl-ca-file'])
    
    if verbose:
        print("Server started at %s://%s:%s with a check interval of %d seconds" % (protocol, config['default']['address'], str(config['default']['port']), int(config['default']['interval'])))
    
    while not thread_stop_requested and not webserver_stop_requested:
        try:
            httpd.handle_request()
        except:
            if verbose:
                print('Webserver died, try to restart ..')
        sleep(1)
    del httpd
    permanent_webserver_thread_running = False
    if verbose:
        print('stopped permanent_webserver_thread')

def restart_webserver():
    global webserver_stop_requested
    global wait_and_check_auto_certificate_thread_stop_requested
    
    tmp_permanent_webserver_thread_running = permanent_webserver_thread_running
    time.sleep(2)
    
    if initialized:
        webserver_stop_requested = True
        wait_and_check_auto_certificate_thread_stop_requested = True
        
        try:
            fake_webserver_request()
        except:
            if stacktrace:
                traceback.print_exc()
        
        while webserver_stop_requested:
            if permanent_webserver_thread_running:
                sleep(1)
            else:
                webserver_stop_requested = False
    
    if tmp_permanent_webserver_thread_running:  # webserver was running before
        # start webserver thread
        permanent_webserver_thread(process_webserver, (enableSSL,))

def create_new_csr(agent_id):
    global ssl_csr
    
    try:
        
        # ECC (not working yet)
        # 
        # from Crypto.PublicKey import ECC
        # 
        # key = ECC.generate(curve='prime256v1')
        # req = X509Req()
        # req.get_subject().CN = agent_id+'.agent.oitc'
        # publicKey = key.public_key().export_key(format='PEM', compress=False)
        # privateKey = key.export_key(format='PEM', compress=False, use_pkcs8=True)
        # 
        # pubdict = {}
        # pubdict['_only_public'] = publicKey
        # req.sign(publicKey, 'sha384')
        
        
        # create public/private key
        key = PKey()
        key.generate_key(TYPE_RSA, 4096)
    
        # Generate CSR
        req = X509Req()
        req.get_subject().CN = agent_id+'.agent.oitc'
        
        
        # Experimental; not supported by php agent csr sign method yet
        san_list = ["DNS:localhost", "DNS:127.0.0.1"]
        req.add_extensions([
            OpenSSL.crypto.X509Extension(b"subjectAltName", True, (", ".join(san_list)).encode('ascii'))
        ])
        
        
        #req.get_subject().O = 'XYZ Widgets Inc'
        #req.get_subject().OU = 'IT Department'
        #req.get_subject().L = 'Seattle'
        #req.get_subject().ST = 'Washington'
        #req.get_subject().C = 'US'
        #req.get_subject().emailAddress = 'e@example.com'
        req.set_pubkey(key)
        req.sign(key, 'sha512')
        
        ssl_paths = [config['default']['autossl-csr-file'], config['default']['autossl-key-file'], config['default']['autossl-crt-file'], config['default']['autossl-ca-file']]
        
        for filename in ssl_paths:
            if not os.path.exists(os.path.dirname(filename)):
                try:
                    os.makedirs(os.path.dirname(filename))
                except OSError as exc: # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        if verbose:
                            print('An error occured while creating the ssl files containing folders')
                        if stacktrace:
                            raise

    
        csr = dump_certificate_request(FILETYPE_PEM, req)
        with open(config['default']['autossl-csr-file'], 'wb+') as f:
            f.write(csr)
        with open(config['default']['autossl-key-file'], 'wb+') as f:
            f.write(dump_privatekey(FILETYPE_PEM, key))
        ssl_csr = csr
            
    except:
        if verbose:
            print('An error occured while creating a new csr')
        if stacktrace:
            traceback.print_exc()
    
    return csr

def pull_crt_from_server(agent_id):
    # pip install pycryptodome pyopenssl
    
    if config['oitc']['url'] is not "" and config['oitc']['apikey'] is not "":
        try:
            csr = create_new_csr(agent_id)
            
            # try to use requests!
            data = bytes(urllib.parse.urlencode({'csr': csr}).encode())
            req = urllib.request.Request(config['oitc']['url'])
            req.add_header('Authorization', 'X-OITC-API '+config['oitc']['apikey'].strip())
            handler = urllib.request.urlopen(req, data)
            
            jdata = json.loads(handler.read().decode('utf-8'))
            if 'unknown' in jdata:  # server dont know agent, manual confirmation in openITCOCKPIT frontend needed
                if verbose:
                    print('Untrusted agent. Try again in 10 minutes to get a certificate from the server.')
                executor = futures.ThreadPoolExecutor(max_workers=1)
                executor.submit(wait_and_check_auto_certificate, 600)
                
            if 'signed' in jdata and 'ca' in jdata:
                with open(config['default']['autossl-crt-file'], 'w+') as f:
                    f.write(jdata['signed'])
                with open(config['default']['autossl-ca-file'], 'w+') as f:
                    f.write(jdata['ca'])
            
                restart_webserver()

                if verbose:
                    print('signed cert updated')
                return True
        except:
            if verbose:
                print('An error occured during autossl certificate renew process')
            if stacktrace:
                traceback.print_exc()
    
    return False

def wait_and_check_auto_certificate(seconds):
    global wait_and_check_auto_certificate_thread_stop_requested
    
    if verbose:
        print('started wait_and_check_auto_certificate')

    if autossl:
        i = 0
        while i < seconds and not wait_and_check_auto_certificate_thread_stop_requested:
            time.sleep(1)
            i = i + 1
        
        if not wait_and_check_auto_certificate_thread_stop_requested:
            doNotWaitForReturnExecutor = futures.ThreadPoolExecutor(max_workers=1)
            doNotWaitForReturnExecutor.submit(check_auto_certificate)
            #check_auto_certificate()
    wait_and_check_auto_certificate_thread_stop_requested = False
    if verbose:
        print('finished wait_and_check_auto_certificate')

def check_auto_certificate():
    if not file_readable(config['default']['autossl-crt-file']):
        pull_crt_from_server(agent_id)
    if file_readable(config['default']['autossl-crt-file']):    # repeat condition because pull_crt_from_server could fail
        with open(config['default']['autossl-crt-file'], 'r') as f:
            cert = f.read()
            x509 = load_certificate(FILETYPE_PEM, cert)
            x509info = x509.get_notAfter()
            exp_day = x509info[6:8].decode('utf-8')
            exp_month = x509info[4:6].decode('utf-8')
            exp_year = x509info[:4].decode('utf-8')
            exp_date = str(exp_day) + "-" + str(exp_month) + "-" + str(exp_year)
            
            if verbose:
                print("SSL Certificate will be expired on (DD-MM-YYYY)", exp_date)
                print("Expire in days:", datetime.date(int(exp_year), int(exp_month), int(exp_day)) - datetime.datetime.now().date())
            
            if datetime.date(int(exp_year), int(exp_month), int(exp_day)) - datetime.datetime.now().date() <= datetime.timedelta(182):
                if verbose:
                    print('SSL Certificate will expire soon. Try to create a new one automatically')
                if pull_crt_from_server(agent_id) is not False:
                    check_auto_certificate()

def print_help():
    print('usage: ./oitc_agent.py -v -i <check interval seconds> -p <port number> -a <ip address> -c <config path> --certfile <certfile path> --keyfile <keyfile path> --auth <user>:<password> --oitc-url <url> --oitc-apikey <api key> --oitc-interval <seconds>')
    print('\nOptions and arguments (overwrite options in config file):')
    print('-i --interval <seconds>      : check interval in seconds')
    print('-p --port <number>           : webserver port number')
    print('-a --address <ip address>    : webserver ip address')
    print('-c --config <config path>    : config file path')
    print('--config-update-mode         : enable config update mode threw post request and /config to get current configuration')
    print('--temperature-fahrenheit     : set temperature to fahrenheit if enabled (else use celsius)')
    print('--customchecks <file path>   : custom check config file path')
    print('--auth <user>:<password>     : enable http basic auth')
    print('-v --verbose                 : enable verbose mode')
    print('-s --stacktrace              : print stacktrace for possible exceptions')
    print('-h --help                    : print this help message and exit')
    print('\nAdd there parameters (all required) to enable transfer of check results to a openITCOCKPIT server:')
    print('--oitc-hostuuid <host uuid>  : host uuid from openITCOCKPIT')
    print('--oitc-url <url>             : openITCOCKPIT url (https://demo.openitcockpit.io)')
    print('--oitc-apikey <api key>      : openITCOCKPIT api key')
    print('--oitc-interval <seconds>    : transfer interval in seconds')
    print('\nAdd there parameters to enable ssl encrypted http(s) server:')
    print('--certfile <certfile path>   : /path/to/cert.pem')
    print('--keyfile <keyfile path>     : /path/to/key.pem')
    print('--try-autossl                : try to enable auto webserver ssl mode')
    print('--disable-autossl            : disable auto webserver ssl mode (overwrite default)')
    print('\nFile paths used for autossl (default: /etc/openitcockpit-agent/... or C:\Program Files\openitcockpit-agent\...):')
    print('--autossl-csr-file <path>    : /path/to/agent.csr')
    print('--autossl-crt-file <path>    : /path/to/agent.crt')
    print('--autossl-key-file <path>    : /path/to/agent.key')
    print('--autossl-ca-file <path>     : /path/to/server_ca.crt')
    print('\nSample config file:')
    print(sample_config)
    print('\nSample config file for custom check commands:')
    print(sample_customcheck_config)

def load_configuration():
    global config
    global verbose
    global stacktrace
    global added_oitc_parameter
    global configpath
    global enableSSL
    global autossl
    global temperatureIsFahrenheit
    
    try:
        opts, args = getopt.getopt(sys.argv[1:],"h:i:p:a:c:vs",["interval=","port=","address=","config=","customchecks=","certfile=","keyfile=","auth=","oitc-hostuuid=","oitc-url=","oitc-apikey=","oitc-interval=","config-update-mode","temperature-fahrenheit","try-autossl","disable-autossl","autossl-csr-file","autossl-crt-file","autossl-key-file","autossl-ca-file","verbose","stacktrace","help"])
    except getopt.GetoptError:
        print_help()
        sys.exit(2)
    
    if isPython3:
        config.read_string(sample_config)
    else:
        config.readfp(io.BytesIO(sample_config))
    
    for opt, arg in opts:
        if opt in ("-c", "--config"):
            configpath = str(arg)
        elif opt in ("-v", "--verbose"):
            verbose = True
        elif opt in ("-s", "--stacktrace"):
            stacktrace = True
    
    if configpath is not "":
        if file_readable(configpath):
            with open(configpath, 'r') as configfile:
                if verbose:
                    print('load agent config file "%s"' % (configpath))
                config.read_file(configfile)
        else:
            with open(configpath, 'w') as configfile:
                if verbose:
                    print('create new default agent config file "%s"' % (configpath))
                config.write(configfile)
    
    config['default']['autossl-csr-file'] = default_ssl_csr_file
    config['default']['autossl-crt-file'] = default_ssl_crt_file
    config['default']['autossl-key-file'] = default_ssl_key_file
    config['default']['autossl-ca-file'] = default_ssl_ca_file
    
    added_oitc_parameter = 0
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print_help()
            sys.exit(0)
        elif opt in ("-i", "--interval"):
            config['default']['interval'] = str(arg)
        elif opt in ("-p", "--port"):
            config['default']['port'] = str(arg)
        elif opt in ("-a", "--address"):
            config['default']['address'] = str(arg)
        elif opt == "--certfile":
            config['default']['certfile'] = str(arg)
        elif opt == "--keyfile":
            config['default']['keyfile'] = str(arg)
        elif opt in ("--try-autossl"):
            config['default']['try-autossl'] = "true"
        elif opt == "--autossl-csr-file":
            config['default']['autossl-csr-file'] = str(arg)
        elif opt == "--autossl-crt-file":
            config['default']['autossl-crt-file'] = str(arg)
        elif opt == "--autossl-key-file":
            config['default']['autossl-key-file'] = str(arg)
        elif opt == "--autossl-ca-file":
            config['default']['autossl-ca-file'] = str(arg)
        elif opt == "--auth":
            config['default']['auth'] = str(base64.b64encode(arg.encode())).encode("utf-8")
        elif opt in ("-v", "--verbose"):
            config['default']['verbose'] = "true"
        elif opt in ("-s", "--stacktrace"):
            config['default']['stacktrace'] = "true"
        elif opt == "--config-update-mode":
            config['default']['config-update-mode'] = "true"
        elif opt == "--temperature-fahrenheit":
            config['default']['temperature-fahrenheit'] = "true"
        elif opt == "--oitc-hostuuid":
            config['oitc']['hostuuid'] = str(arg)
            added_oitc_parameter += 1
        elif opt == "--oitc-url":
            config['oitc']['url'] = str(arg)
            added_oitc_parameter += 1
        elif opt == "--oitc-apikey":
            config['oitc']['apikey'] = str(arg)
            added_oitc_parameter += 1
        elif opt == "--oitc-interval":
            config['oitc']['interval'] = str(arg)
            added_oitc_parameter += 1
        elif opt == "--customchecks":
            config['default']['customchecks'] = str(arg)
    
    # loop again to for default overwrite options
    for opt, arg in opts:
        if opt in ("--disable-autossl"):
            config['default']['try-autossl'] = "false"
            break;
    
    if config['default']['verbose'] in (1, "1", "true", "True", True):
        verbose = True
    else:
        verbose = False
    
    if config['default']['stacktrace'] in (1, "1", "true", "True", True):
        stacktrace = True
    else:
        stacktrace = False
    
    if config['default']['try-autossl'] in (1, "1", "true", "True", True):
        autossl = True
    else:
        autossl = False
    
    
    if config['default']['temperature-fahrenheit'] in (1, "1", "true", "True", True):
        temperatureIsFahrenheit = True
    else:
        temperatureIsFahrenheit = False
    
    if 'auth' in config['default'] and str(config['default']['auth']).strip():
        if not isBase64(config['default']['auth']):
            if isPython3:
                config['default']['auth'] = str(base64.b64encode(config['default']['auth'].encode()), "utf-8")
            else:
                config['default']['auth'] = str(base64.b64encode(config['default']['auth'].encode())).encode("utf-8")
    
    if config['default']['certfile'] != "" and config['default']['keyfile'] != "":
        try:
            if file_readable(config['default']['certfile']) and file_readable(config['default']['keyfile']):
                enableSSL = True
            elif verbose:
                print("could not read certfile or keyfile\nfall back to default http server")
            
        except IOError:
            if verbose:
                print("could not read certfile or keyfile\nfall back to default http server")
    
def fake_webserver_request():
    protocol = 'http'
    if enableSSL:
        protocol = 'https'
    complete_address = protocol + '://' + config['default']['address'] + ':' + str(config['default']['port'])

    if isPython3:
        urllib.request.urlopen(complete_address).read()
    else:
        urllib2.urlopen(complete_address).read()
    
def reload_all():
    global thread_stop_requested
    
    if initialized:
        thread_stop_requested = True
        
        try:
            fake_webserver_request()
        except:
            if stacktrace:
                traceback.print_exc()
        
        while thread_stop_requested:
            if permanent_check_thread_running or permanent_webserver_thread_running or oitc_notification_thread_running or permanent_customchecks_check_thread_running:
                sleep(1)
            else:
                thread_stop_requested = False
        reset_global_options()
    
    load_configuration()
    return True
    
def load_main_processing():
    global initialized
    
    while not reload_all():
        sleep(1)
    
    if autossl:
        check_auto_certificate()    #need to be called before initialized = True to prevent webserver thread restart
    
    initialized = True
    
    if 'oitc' in config and (config['oitc']['enabled'] in (1, "1", "true", "True", True) or added_oitc_parameter == 4):
        oitc_notification_thread(notify_oitc, (config['oitc'],))
    
    if config['default']['customchecks'] != "":
        if file_readable(config['default']['customchecks']):
            with open(config['default']['customchecks'], 'r') as customchecks_configfile:
                if verbose:
                    print('load custom check config file "%s"' % (config['default']['customchecks']))
                customchecks.read_file(customchecks_configfile)
            if customchecks:
                permanent_customchecks_check_thread(collect_customchecks_data_for_cache, (customchecks,))
                
    permanent_check_thread(collect_data_for_cache, (int(config['default']['interval']),))
    permanent_webserver_thread(process_webserver, (enableSSL,))

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    load_main_processing()
    
    try:
        while True:
            signal.pause()
    except AttributeError:
        # signal.pause() is missing for Windows; wait 1ms and loop instead
        while True:
            time.sleep(1)

