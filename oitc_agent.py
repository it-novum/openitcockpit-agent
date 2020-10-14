#!/usr/bin/python

#    Copyright 2020, it-novum GmbH
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# supports python2.7 and python3.7 (recommended)
#
# current psutil>=5.5.0,<=5.6.2 limitation due to https://github.com/giampaolo/psutil/issues/1723



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
import requests
import hashlib
import logging

from os import access, R_OK, devnull
from os.path import isfile
from time import sleep
from contextlib import contextmanager
from OpenSSL.SSL import FILETYPE_PEM
from OpenSSL.crypto import (dump_certificate_request, dump_privatekey, load_certificate, PKey, TYPE_RSA, X509Req)
from logging.handlers import RotatingFileHandler

isPython3 = False
system = 'linux'
jmx_import_successfull = False




if sys.platform == 'win32' or sys.platform == 'win64':
    system = 'windows'
    import win32evtlog
    import win32evtlogutil
    import win32con
    import win32security # To translate NT Sids to account names.
if sys.platform == 'darwin' or (system == 'linux' and 'linux' not in sys.platform):
    system = 'darwin'

log_formatter = logging.Formatter('%(asctime)s; %(levelname)s; %(lineno)d; %(message)s')
agent_log_path = '/etc/openitcockpit-agent/'
if system == 'darwin':
    agent_log_path = '/Library/openitcockpit-agent/'
if system == 'windows':
    agent_log_path = 'C:'+os.path.sep+'Program Files'+os.path.sep+'it-novum'+os.path.sep+'openitcockpit-agent'+os.path.sep

logfile = agent_log_path + 'agent.log'

logfile_handler = RotatingFileHandler(logfile, mode='a', maxBytes=10*1024*1024, backupCount=2, encoding=None, delay=0)
logfile_handler.setFormatter(log_formatter)
logfile_handler.setLevel(logging.DEBUG)

agent_log = logging.getLogger('root')
agent_log.setLevel(logging.DEBUG)

agent_log.addHandler(logfile_handler)

agent_log.info('Agent started')

if (sys.version_info >= (3, 0)):
    isPython3 = True
    import concurrent.futures as futures
    import subprocess

    from threading import Thread, Lock
    from _thread import start_new_thread as update_crt_files_thread
    from _thread import start_new_thread as permanent_check_thread
    from _thread import start_new_thread as permanent_webserver_thread
    from _thread import start_new_thread as oitc_notification_thread
    from _thread import start_new_thread as permanent_customchecks_check_thread
    from socketserver import ThreadingMixIn
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
    agent_log.warning('Python 2 is End Of Life and will not be maintained past  January 1, 2020! Update your system to Python 3!')
    
    import subprocess32 as subprocess
    
    from concurrent import futures
    from threading import Thread, Lock
    from thread import start_new_thread as update_crt_files_thread
    from thread import start_new_thread as permanent_check_thread
    from thread import start_new_thread as permanent_webserver_thread
    from thread import start_new_thread as oitc_notification_thread
    from thread import start_new_thread as permanent_customchecks_check_thread
    from SocketServer import ThreadingMixIn
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    ProcessLookupError = None
    
try:
    import psutil
    if isPython3 and psutil.version_info < (5, 5, 0):
        print('psutil >= 5.5.0 required!')
        agent_log.error('psutil >= 5.5.0 required!')
        raise ImportError('psutil version too old!')
        
except ImportError:
    if system == 'windows':
        print('Install Python psutil: python.exe -m pip install psutil')
        agent_log.error('Install Python psutil: python.exe -m pip install psutil')
    elif system == 'linux' and isPython3:
        print('Install Python psutil: pip3 install psutil or apt-get install python3-psutil')
        agent_log.error('Install Python psutil: pip3 install psutil or apt-get install python3-psutil')
    elif system == 'linux' and not isPython3:
        print('Install Python psutil: pip install psutil or apt-get install python-psutil')
        agent_log.error('Install Python psutil: pip install psutil or apt-get install python-psutil')
    else:
        print('Install Python psutil: pip install psutil')
        agent_log.error('Install Python psutil: pip install psutil')
    sys.exit(1)
    
try:
    from jmxquery import JMXConnection, JMXQuery, JMXConnection
    jmx_import_successfull = True
except:
    print('jmxquery not found!')
    agent_log.info('jmxquery not found!')
    if isPython3:
        print('If you want to use the alfresco stats check try: pip3 install jmxquery')
        agent_log.info('If you want to use the alfresco stats check try: pip3 install jmxquery')
    else:
        print('If you want to use the alfresco stats check try: pip install jmxquery')
        agent_log.info('If you want to use the alfresco stats check try: pip install jmxquery')

agentVersion = "1.0.5"
days_until_cert_warning = 120
days_until_ca_warning = 30
enableSSL = False
autossl = True
cached_check_data = {}
cached_customchecks_check_data = {}
docker_stats_data = {}
qemu_stats_data = {}
alfresco_stats_data = {}
systemd_services_data = {}
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

update_crt_files_thread_running = False
permanent_check_thread_running = False
permanent_webserver_thread_running = False
oitc_notification_thread_running = False
permanent_customchecks_check_thread_running = False

cert_checksum = ''
ssl_csr = None
sha512 = hashlib.sha512()
print_lock = Lock()
certificate_check_lock = Lock()

sample_config = """
[default]
  interval = 30
  port = 3333
  address = 0.0.0.0
  certfile = 
  keyfile = 
  try-autossl = true
  autossl-folder = 
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
  dockerstats = false
  qemustats = false
  cpustats = true
  sensorstats = true
  processstats = true
  processstats-including-child-ids = false
  netstats = true
  diskstats = true
  netio = true
  diskio = true
  winservices = true
  systemdservices = true
  wineventlog = true
  wineventlog-logtypes = System, Application, Security, openITCOCKPIT Agent
  
  alfrescostats = false
  alfresco-jmxuser = monitorRole
  alfresco-jmxpassword = change_asap
  alfresco-jmxaddress = 0.0.0.0
  alfresco-jmxport = 50500
  alfresco-jmxpath = /alfresco/jmxrmi
  alfresco-jmxquery = 
  alfresco-javapath = /usr/bin/java

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
  max_worker_threads = 8
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
    """Function to reset global variables / objects
    
    Called on agent reload.
    Threads need to be stopped before running this function!

    """
    globals()['enableSSL'] = False
    globals()['cached_check_data'] = {}
    globals()['cached_customchecks_check_data'] = {}
    globals()['docker_stats_data'] = {}
    globals()['qemu_stats_data'] = {}
    globals()['alfresco_stats_data'] = {}
    globals()['systemd_services_data'] = {}
    globals()['configpath'] = ""
    globals()['verbose'] = False
    globals()['stacktrace'] = False
    globals()['added_oitc_parameter'] = 0
    globals()['initialized'] = False
    globals()['thread_stop_requested'] = False
    globals()['update_crt_files_thread_running'] = False
    globals()['permanent_check_thread_running'] = False
    globals()['permanent_webserver_thread_running'] = False
    globals()['oitc_notification_thread_running'] = False
    globals()['permanent_customchecks_check_thread_running'] = False
    globals()['config'] = configparser.ConfigParser(allow_no_value=True)
    globals()['customchecks'] = configparser.ConfigParser(allow_no_value=True)


def print_verbose(msg, more_on_stacktrace):
    """Function to print verbose output uniformly and prevent double verbose output at the same time
    
    Print verbose output and add stacktrace hint if requested.
    Uses a lock to prevent duplicate verbose output at the same time,
    which would result in one of the outputs not being displayed.

    Parameters
    ----------
    msg
        Message string
    more_on_stacktrace
        Boolean to decide whether the stacktrace hint will be printed or not

    """
    with print_lock:
        if verbose:
            print(msg)
        if not stacktrace and more_on_stacktrace and verbose:
            print("Enable --stacktrace to get more information.")


def print_verbose_without_lock(msg, more_on_stacktrace):
    """Function to directly print verbose output uniformly
    
    Print verbose output and add stacktrace hint if requested.

    Parameters
    ----------
    msg
        Message string
    more_on_stacktrace
        Boolean to decide whether the stacktrace hint will be printed or not

    """
    if verbose:
        print(msg)
    if not stacktrace and more_on_stacktrace and verbose:
        print("Enable --stacktrace to get more information.")


def signal_handler(sig, frame):
    """A custom signal handler to stop the agent if it is called"""
    global thread_stop_requested
    global webserver_stop_requested
    global wait_and_check_auto_certificate_thread_stop_requested
    
    thread_stop_requested = True
    webserver_stop_requested = True
    wait_and_check_auto_certificate_thread_stop_requested = True
    agent_log.info("Agent stopped")
    
    if verbose:
        print("Agent stopped\n")
    sys.exit(0)

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
    """ Function to calculate the difference between last and curr
    
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


def build_autossl_defaults():
    """ Function to define the system depending certificate file paths

        Certificate file default paths:

        - Windows:        C:\Program Files\openitcockpit-agent\agent.crt
        - Linux:          /etc/openitcockpit-agent/agent.crt
        - macOS:          /etc/openitcockpit-agent/agent.crt

        Config file default paths:

        - Windows:        C:\Program Files\openitcockpit-agent\config.cnf
        - Linux:          /etc/openitcockpit-agent/config.cnf
        - macOS:          /Library/openitcockpit-agent/config.cnf

    """
    etc_agent_path = '/etc/openitcockpit-agent/'
    if system == 'windows':
        etc_agent_path = 'C:'+os.path.sep+'Program Files'+os.path.sep+'it-novum'+os.path.sep+'openitcockpit-agent'+os.path.sep
    
    if config['default']['autossl-folder'] != "":
        etc_agent_path = config['default']['autossl-folder'] + os.path.sep
    
    config['default']['autossl-csr-file'] = etc_agent_path + 'agent.csr'
    config['default']['autossl-crt-file'] = etc_agent_path + 'agent.crt'
    config['default']['autossl-key-file'] = etc_agent_path + 'agent.key'
    config['default']['autossl-ca-file'] = etc_agent_path + 'server_ca.crt'


def run_default_checks():
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
    agent_log.info('Running default checks')
    global cached_diskIO
    global cached_netIO
    
    if verbose:
        print_lock.acquire()
        
    if config['default']['cpustats'] in (1, "1", "true", "True"):
    
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
        agent_log.error("Could not get system uptime!")
        print_verbose_without_lock("Could not get system uptime!", True)
        
        if stacktrace:
            traceback.print_exc()
            

    #totalCpus = psutil.cpu_count()
    #physicalCpus = psutil.cpu_count(logical=False)

    #cpuFrequency = psutil.cpu_freq()

    # MEMORY #

    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    if config['default']['diskstats'] in (1, "1", "true", "True"):
        # DISKS #
        disks = []
        try:
            for disk in psutil.disk_partitions():
                if os.name == 'nt':
                    if 'cdrom' in disk.opts or disk.fstype == '':
                        # skip cd-rom drives with no disk in it; they may raise
                        # ENOENT, pop-up a Windows GUI error for a non-ready
                        # partition or just hang.
                        continue
                disks.append(dict(
                    disk = disk._asdict(),
                    usage = psutil.disk_usage(disk.mountpoint)._asdict()
                    ))
        except:
            agent_log.error("Could not get system disks!")
            print_verbose_without_lock("Could not get system disks!", True)
            
            if stacktrace:
                traceback.print_exc()
                
    
    diskIO = None
    if hasattr(psutil, "disk_io_counters") and config['default']['diskio'] in (1, "1", "true", "True"):
        try:
            #diskIOTotal = psutil.disk_io_counters(perdisk=False)._asdict()
            #diskIO = psutil.disk_io_counters(perdisk=True)
            diskIO = { disk: iops._asdict() for disk,iops in psutil.disk_io_counters(perdisk=True).items() }
            diskIO['timestamp'] = time.time()

            for disk in diskIO:
                if disk != "timestamp" and disk in cached_diskIO:

                    diskIODiff = {}
                    diskIODiff['timestamp'] = wrapdiff(float(cached_diskIO['timestamp']), float(diskIO['timestamp']))

                    for attr in diskIO[disk]:
                        diff = wrapdiff(float(cached_diskIO[disk][attr]), float(diskIO[disk][attr]))
                        diskIODiff[attr] = diff

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
        except:
            print_verbose_without_lock("Could not get disk io stats!", True)
            agent_log.error("Could not get disk io stats!")
            
            if stacktrace:
                traceback.print_exc()
                
    
    netIO = None
    if hasattr(psutil, "net_io_counters") and config['default']['netio'] in (1, "1", "true", "True"):
        try:
            netIO = { device: data._asdict() for device,data in psutil.net_io_counters(pernic=True).items() }
            netIO['timestamp'] = time.time()

            for device in netIO:
                if device != "timestamp" and device in cached_netIO:

                    netIODiff = {}
                    netIODiff['timestamp'] = wrapdiff(float(cached_netIO['timestamp']), float(netIO['timestamp']))

                    for attr in netIO[device]:
                        diff = wrapdiff(float(cached_netIO[device][attr]), float(netIO[device][attr]))
                        netIODiff[attr] = diff

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
        except:
            print_verbose_without_lock("Could not get network io stats!", True)
            agent_log.error("Could not get network io stats!")
            
            if stacktrace:
                traceback.print_exc()
                
    
    net_stats = None
    if hasattr(psutil, "net_if_stats") and config['default']['netstats'] in (1, "1", "true", "True"):
        try:
            net_stats = { device: data._asdict() for device,data in psutil.net_if_stats().items() }
        except:
            print_verbose_without_lock("Could not get network device stats!", True)
            agent_log.error("Could not get network device stats!")
            
            if stacktrace:
                traceback.print_exc()
                

    sensors = {}
    if config['default']['sensorstats'] in (1, "1", "true", "True"):
        try:
            if hasattr(psutil, "sensors_temperatures") and system != 'windows':
                sensors['temperatures'] = {}
                for device,data in psutil.sensors_temperatures(fahrenheit=temperatureIsFahrenheit).items():
                    sensors['temperatures'][device] = []
                    for value in data:
                        sensors['temperatures'][device].append(value._asdict())
            else:
                sensors['temperatures'] = {}
        except:
            print_verbose_without_lock("Could not get temperature sensor data!", True)
            agent_log.error("Could not get temperature sensor data!")
            
            if stacktrace:
                traceback.print_exc()
                
        
        try:
            if hasattr(psutil, "sensors_fans") and system != 'windows':
                sensors['fans'] = {}
                for device,data in psutil.sensors_fans().items():
                    sensors['fans'][device] = []
                    for value in data:
                        sensors['fans'][device].append(value._asdict())
            else:
                sensors['fans'] = {}
        except:
            print_verbose_without_lock("Could not get fans sensor data!", True)
            agent_log.error("Could not get fans sensor data!")
            
            if stacktrace:
                traceback.print_exc()
                
        
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
            print_verbose_without_lock("Could not get battery sensor data!", True)
            agent_log.error("Could not get battery sensor data!")
            
            if stacktrace:
                traceback.print_exc()
                
    
    if hasattr(psutil, "pids"):
        pids = psutil.pids()
    else:
        pids = psutil.get_pid_list()
    
    system_load_avg = []
    try:
        if hasattr(psutil, "getloadavg"):
            system_load_avg = psutil.getloadavg()
        elif hasattr(os, "getloadavg"):
            system_load_avg = os.getloadavg()
    except:
        print_verbose_without_lock("Could not get average system load!", True)
        agent_log.error("Could not get average system load!")
        
        if stacktrace:
            traceback.print_exc()
            
            
    users = []
    try:
        if hasattr(psutil, "users"):
            users = [ user._asdict() for user in psutil.users() ]
    except:
        print_verbose_without_lock("Could not get users, connected to the system!", True)
        agent_log.error("Could not get users, connected to the system!")
        
        if stacktrace:
            traceback.print_exc()
            
        

    #processes = [ psutil.Process(pid).as_dict() for pid in pids ]
    processes = []
    customchecks = {}
    
    tmpProcessList = []
    
    if config['default']['processstats'] in (1, "1", "true", "True"):
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
                    print_verbose_without_lock("'%s' Process is not allowing us to get the CPU usage!" % (name if name != "" else str(pid)), True)
                    #agent_log.error("'%s' Process is not allowing us to get the CPU usage!" % (name if name != "" else str(pid)))
                    
                    if stacktrace:
                        traceback.print_exc()
                        
            
            except psutil.NoSuchProcess:
                continue
            except:
                print_verbose_without_lock("An error occured during process check!", True)
                agent_log.error("An error occured during process check!")
                
                if stacktrace:
                    traceback.print_exc()
                    
    
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
                    continue
                except AttributeError:
                    print_verbose_without_lock("'%s' Process is not allowing us to get the parent process id!" % (str(pid)), True)
                    #agent_log.error("'%s' Process is not allowing us to get the parent process id!" % (str(pid)))
                    
                    if stacktrace:
                        traceback.print_exc()
                        
                
                if config['default']['processstats-including-child-ids'] in (1, "1", "true", "True"):
                    try:
                        if callable(p.children):
                            with suppress_stdout_stderr():
                                for child in p.children(recursive=True):
                                    children.append(child.pid)
                    except:
                        print_verbose_without_lock("'%s' Process is not allowing us to get the child process ids!" % (str(pid)), True)
                        #agent_log.error("'%s' Process is not allowing us to get the child process ids!" % (str(pid)))
                        
                        if stacktrace:
                            traceback.print_exc()
                            
            
            
            try:
                nice = p.nice()
            except (psutil.NoSuchProcess, ProcessLookupError):
                continue
            except:
                print_verbose_without_lock("'%s' Process is not allowing us to get the nice option!" % (name if name != "" else str(pid)), True)
                #agent_log.error("'%s' Process is not allowing us to get the nice option!" % (name if name != "" else str(pid)))
                
                if stacktrace:
                    traceback.print_exc()
                    
        
            try:
                name = p.name()
            except (psutil.NoSuchProcess, ProcessLookupError):
                continue
            except:
                print_verbose_without_lock("'%s' Process is not allowing us to get the name option!" % (name if name != "" else str(pid)), True)
                #agent_log.error("'%s' Process is not allowing us to get the name option!" % (name if name != "" else str(pid)))
                
                if stacktrace:
                    traceback.print_exc()
                    
            try:
                username = p.username()
            except (psutil.NoSuchProcess, ProcessLookupError):
                continue
            except:
                print_verbose_without_lock("'%s' Process is not allowing us to get the username option!" % (name if name != "" else str(pid)), True)
                #agent_log.error("'%s' Process is not allowing us to get the username option!" % (name if name != "" else str(pid)))
                
                if stacktrace:
                    traceback.print_exc()
        
            try:
                exe = p.exe()
            except (psutil.NoSuchProcess, ProcessLookupError):
                continue
            except:
                print_verbose_without_lock("'%s' Process is not allowing us to get the exec option!" % (name if name != "" else str(pid)), True)
                #agent_log.error("'%s' Process is not allowing us to get the exec option!" % (name if name != "" else str(pid)))
                
                if stacktrace:
                    traceback.print_exc()
                    
            
            try:
                cmdline = p.cmdline()
            except (psutil.NoSuchProcess, ProcessLookupError):
                continue
            except:
                print_verbose_without_lock("'%s' Process is not allowing us to get the cmdline option!" % (name if name != "" else str(pid)), True)
                #agent_log.error("'%s' Process is not allowing us to get the cmdline option!" % (name if name != "" else str(pid)))
                
                if stacktrace:
                    traceback.print_exc()
                    
                
            try:
                cpu_percent = p.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, ProcessLookupError):
                continue
            except:
                print_verbose_without_lock("'%s' Process is not allowing us to get the CPU usage!" % (name if name != "" else str(pid)), True)
                #agent_log.error("'%s' Process is not allowing us to get the CPU usage!" % (name if name != "" else str(pid)))
                
                if stacktrace:
                    traceback.print_exc()
                    
                
            try:
                memory_info = p.memory_info()._asdict()
            except (psutil.NoSuchProcess, ProcessLookupError):
                continue
            except:
                print_verbose_without_lock("'%s' Process is not allowing us to get memory usage information!" % (name if name != "" else str(pid)), True)
                #agent_log.error("'%s' Process is not allowing us to get memory usage information!" % (name if name != "" else str(pid)))
                
                if stacktrace:
                    traceback.print_exc()
                    
                
            try:
                memory_percent = p.memory_percent()
            except (psutil.NoSuchProcess, ProcessLookupError):
                continue
            except:
                print_verbose_without_lock("'%s' Process is not allowing us to get the percent of memory usage!" % (name if name != "" else str(pid)), True)
                #agent_log.error("'%s' Process is not allowing us to get the percent of memory usage!" % (name if name != "" else str(pid)))
                
                if stacktrace:
                    traceback.print_exc()
                    
                
            try:
                num_fds = p.num_fds()
            except (psutil.NoSuchProcess, ProcessLookupError):
                continue
            except:
                print_verbose_without_lock("'%s' Process is not allowing us to get the num_fds option!" % (name if name != "" else str(pid)), True)
                #agent_log.error("'%s' Process is not allowing us to get the num_fds option!" % (name if name != "" else str(pid)))
                
                if stacktrace:
                    traceback.print_exc()
                    
            
            try:
                io_counters = p.io_counters.__dict__
            except (psutil.NoSuchProcess, ProcessLookupError):
                continue
            except:
                print_verbose_without_lock("'%s' Process is not allowing us to get the IO counters!" % (name if name != "" else str(pid)), True)
                #agent_log.error("'%s' Process is not allowing us to get the IO counters!" % (name if name != "" else str(pid)))
                
                if stacktrace:
                    traceback.print_exc()
                    
            
            try:
                open_files = p.open_files()
            except (psutil.NoSuchProcess, ProcessLookupError):
                continue
            except psutil.AccessDenied:
                print_verbose_without_lock("'%s' Process is not allowing us to get the open_files option!" % (name if name != "" else str(pid)), True)
                #agent_log.error("'%s' Process is not allowing us to get the open_files option!" % (name if name != "" else str(pid)))
                
                if stacktrace:
                    traceback.print_exc()

            name = name[:1000]
            exe = exe[:1000]
            cmdline = cmdline[:1000]
                
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
            continue
        except:
            print_verbose_without_lock("An error occured during process check!", True)
            agent_log.error("An error occured during process check!")
            
            if stacktrace:
                traceback.print_exc()
                

    windows_services = []
    windows_eventlog = {}
    if system == 'windows':
        if config['default']['winservices'] in (1, "1", "true", "True"):
            try:
                for win_process in psutil.win_service_iter():
                    windows_services.append(win_process.as_dict())
            except:
                print_verbose_without_lock("An error occured during windows services check!", True)
                agent_log.error("An error occured during windows services check!")
                
                if stacktrace:
                    traceback.print_exc()
                    
        if config['default']['wineventlog'] in (1, "1", "true", "True"):
            try:
                server = 'localhost'    # name of the target computer to get event logs
                logTypes = []
                if config['default']['wineventlog-logtypes'] != "":
                    for logtype in config['default']['wineventlog-logtypes'].split(','):
                        if logtype.strip() != '':
                            logTypes.append(logtype.strip())
                else:
                    logTypes = ['System', 'Application', 'Security', 'openITCOCKPIT Agent']

                evt_dict={
                    win32con.EVENTLOG_AUDIT_FAILURE:'EVENTLOG_AUDIT_FAILURE',           # 16 -> critical
                    win32con.EVENTLOG_AUDIT_SUCCESS:'EVENTLOG_AUDIT_SUCCESS',           # 8  -> ok
                    win32con.EVENTLOG_INFORMATION_TYPE:'EVENTLOG_INFORMATION_TYPE',     # 4  -> ok
                    win32con.EVENTLOG_WARNING_TYPE:'EVENTLOG_WARNING_TYPE',             # 2  -> warning
                    win32con.EVENTLOG_ERROR_TYPE:'EVENTLOG_ERROR_TYPE'                  # 1  -> critical
                }

                for logType in logTypes:
                    try:
                        if logType not in windows_eventlog:
                            windows_eventlog[logType] = []
                        hand = win32evtlog.OpenEventLog(server,logType)
                        flags = win32evtlog.EVENTLOG_BACKWARDS_READ|win32evtlog.EVENTLOG_SEQUENTIAL_READ
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
                                    'event_data': [ data for data in event.StringInserts ] if event.StringInserts else ''
                                }
                                windows_eventlog[logType].append(tmp_evt)
                    except:
                        print_verbose_without_lock("An error occured during windows eventlog check with log type %s!" % (logType), True)
                        agent_log.error("An error occured during windows eventlog check with log type %s!" % (logType))
                        
                        if stacktrace:
                            traceback.print_exc()
                            
            except:
                print_verbose_without_lock("An error occured during windows eventlog check!", True)
                agent_log.error("An error occured during windows eventlog check!")
                
                if stacktrace:
                    traceback.print_exc()
                    

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
        'agent': agent,
        #'disks': disks,
        #'disk_io': diskIO,
        #'disk_io_total': diskIOTotal,
        #'net_stats': net_stats,
        #'net_io': netIO,
        
        #'sensors': sensors,

        #'cpu_total_percentage': cpuTotalPercentage,
        #'cpu_percentage': cpuPercentage,
        #'cpu_total_percentage_detailed': cpuTotalPercentageDetailed,
        #'cpu_percentage_detailed': cpuPercentageDetailed,
        
        'system_load': system_load_avg,
        'users': users,
        
        'memory': memory._asdict(),
        'swap': swap._asdict(),

        #'processes': processes
    }
        
    if config['default']['diskstats'] in (1, "1", "true", "True"):
        out['disks'] = disks
        
    if config['default']['diskio'] in (1, "1", "true", "True"):
        out['disk_io'] = diskIO
        
    if config['default']['netstats'] in (1, "1", "true", "True"):
        out['net_stats'] = net_stats
        
    if config['default']['netio'] in (1, "1", "true", "True"):
        out['net_io'] = netIO
        
    if config['default']['sensorstats'] in (1, "1", "true", "True"):
        out['sensors'] = sensors
        
    if config['default']['cpustats'] in (1, "1", "true", "True"):
        out['cpu_total_percentage'] = cpuTotalPercentage
        out['cpu_percentage'] = cpuPercentage
        out['cpu_total_percentage_detailed'] = cpuTotalPercentageDetailed
        out['cpu_percentage_detailed'] = cpuPercentageDetailed
        
    if config['default']['processstats'] in (1, "1", "true", "True"):
        out['processes'] = processes
    
    if system == 'windows':
        if config['default']['winservices'] in (1, "1", "true", "True"):
            out['windows_services'] = windows_services
        if config['default']['wineventlog'] in (1, "1", "true", "True"):
            out['windows_eventlog'] = windows_eventlog
        
    if len(systemd_services_data) > 0:
        out['systemd_services'] = systemd_services_data
        
    if len(cached_customchecks_check_data) > 0:
        out['customchecks'] = cached_customchecks_check_data
        
    if len(docker_stats_data) > 0:
        out['dockerstats'] = docker_stats_data
        
    if len(qemu_stats_data) > 0:
        out['qemustats'] = qemu_stats_data
        
    if 'result' in alfresco_stats_data and config['default']['alfrescostats'] in (1, "1", "true", "True"):
        out['alfrescostats'] = alfresco_stats_data['result']
        
    #if jmx_import_successfull and 'alfrescostats' in config['default'] and config['default']['alfrescostats'] in (1, "1", "true", "True", True):
    #    out['alfrescostats'] = alfrescostats
    if verbose:
        print_lock.release()
    return out


def file_readable(path):
    """Function to check whether a file is readable or not
    
    Parameters
    ----------
    path
        Path to file

    """
    return (isfile(path) and access(path, R_OK))


def is_base64(s):
    """Function to check whether a string is base64 encoded or not
    
    Parameters
    ----------
    s
        String to check

    """
    try:
        return base64.b64encode(base64.b64decode(s)) == s
    except Exception:
        return False


def update_crt_files(data):
    """Function to update the certificate files
    
    Update the automatically generated agent certificate file and the ca certificate file if they are writeable.
    Update the cached certificate checksum.

    Parameters
    ----------
    data
        Object containing 'signed'(certificate file) and 'ca'(ca certificate) contents.

    """
    agent_log.info('update crt files')
    global cert_checksum
    global update_crt_files_thread_running

    if update_crt_files_thread_running:
        return False

    update_crt_files_thread_running = True
    
    try:
        jdata = json.loads(data.decode('utf-8'))
        jxdata = json.loads(jdata)
        if 'signed' in jdata and 'ca' in jdata:
            with open(config['default']['autossl-crt-file'], 'w+') as f:
                f.write(jxdata['signed'])
                sha512.update(jxdata['signed'].encode())
                cert_checksum = sha512.hexdigest().upper()
            with open(config['default']['autossl-ca-file'], 'w+') as f:
                f.write(jxdata['ca'])
            
            restart_webserver()
        
    except Exception as e:
        print_verbose("An error occured during new certificate processing", True)
        agent_log.error("An error occured during new certificate processing")
        agent_log.exception(e)
        
        if stacktrace:
            traceback.print_exc()
            print(e)
            
    update_crt_files_thread_running = False

        
def check_update_data(data):
    """Function that starts as a thread (future) to check and update the agent configuration
    
    The POST Data Object will be parsed as valid json object.
    The configuration options are loaded into the configparser objects and will be written to the configfiles(if defined).
    After that an agent reload will be triggered calling load_main_processing().

    Parameters
    ----------
    data
        POST Data Object from webserver

    """
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
                if 'autossl-folder' in jdata[key]:
                    newconfig['default']['autossl-folder'] = str(jdata[key]['autossl-folder'])
                if 'autossl-csr-file' in jdata[key]:
                    newconfig['default']['autossl-csr-file'] = str(jdata[key]['autossl-csr-file'])
                if 'autossl-crt-file' in jdata[key]:
                    newconfig['default']['autossl-crt-file'] = str(jdata[key]['autossl-crt-file'])
                if 'autossl-key-file' in jdata[key]:
                    newconfig['default']['autossl-key-file'] = str(jdata[key]['autossl-key-file'])
                if 'autossl-ca-file' in jdata[key]:
                    newconfig['default']['autossl-ca-file'] = str(jdata[key]['autossl-ca-file'])
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
                if 'dockerstats' in jdata[key]:
                    if jdata[key]['dockerstats'] in (1, "1", "true", "True"):
                        newconfig['default']['dockerstats'] = "true"
                    else:
                        newconfig['default']['dockerstats'] = "false"
                if 'qemustats' in jdata[key]:
                    if jdata[key]['qemustats'] in (1, "1", "true", "True"):
                        newconfig['default']['qemustats'] = "true"
                    else:
                        newconfig['default']['qemustats'] = "false"
                if 'cpustats' in jdata[key]:
                    if jdata[key]['cpustats'] in (1, "1", "true", "True"):
                        newconfig['default']['cpustats'] = "true"
                    else:
                        newconfig['default']['cpustats'] = "false"
                if 'sensorstats' in jdata[key]:
                    if jdata[key]['sensorstats'] in (1, "1", "true", "True"):
                        newconfig['default']['sensorstats'] = "true"
                    else:
                        newconfig['default']['sensorstats'] = "false"
                if 'processstats' in jdata[key]:
                    if jdata[key]['processstats'] in (1, "1", "true", "True"):
                        newconfig['default']['processstats'] = "true"
                    else:
                        newconfig['default']['processstats'] = "false"
                if 'processstats-including-child-ids' in jdata[key]:
                    if jdata[key]['processstats-including-child-ids'] in (1, "1", "true", "True"):
                        newconfig['default']['processstats-including-child-ids'] = "true"
                    else:
                        newconfig['default']['processstats-including-child-ids'] = "false"
                if 'netstats' in jdata[key]:
                    if jdata[key]['netstats'] in (1, "1", "true", "True"):
                        newconfig['default']['netstats'] = "true"
                    else:
                        newconfig['default']['netstats'] = "false"
                if 'diskstats' in jdata[key]:
                    if jdata[key]['diskstats'] in (1, "1", "true", "True"):
                        newconfig['default']['diskstats'] = "true"
                    else:
                        newconfig['default']['diskstats'] = "false"
                if 'netio' in jdata[key]:
                    if jdata[key]['netio'] in (1, "1", "true", "True"):
                        newconfig['default']['netio'] = "true"
                    else:
                        newconfig['default']['netio'] = "false"
                if 'diskio' in jdata[key]:
                    if jdata[key]['diskio'] in (1, "1", "true", "True"):
                        newconfig['default']['diskio'] = "true"
                    else:
                        newconfig['default']['diskio'] = "false"
                if 'winservices' in jdata[key]:
                    if jdata[key]['winservices'] in (1, "1", "true", "True"):
                        newconfig['default']['winservices'] = "true"
                    else:
                        newconfig['default']['winservices'] = "false"
                if 'systemdservices' in jdata[key]:
                    if jdata[key]['systemdservices'] in (1, "1", "true", "True"):
                        newconfig['default']['systemdservices'] = "true"
                    else:
                        newconfig['default']['systemdservices'] = "false"
                if 'wineventlog' in jdata[key]:
                    if jdata[key]['wineventlog'] in (1, "1", "true", "True"):
                        newconfig['default']['wineventlog'] = "true"
                    else:
                        newconfig['default']['wineventlog'] = "false"
                if 'wineventlog-logtypes' in jdata[key]:
                    newconfig['default']['wineventlog-logtypes'] = str(jdata[key]['wineventlog-logtypes'])
                
                if 'alfrescostats' in jdata[key]:
                    if jdata[key]['alfrescostats'] in (1, "1", "true", "True"):
                        newconfig['default']['alfrescostats'] = "true"
                    else:
                        newconfig['default']['alfrescostats'] = "false"
                if 'alfresco-jmxuser' in jdata[key]:
                    newconfig['default']['alfresco-jmxuser'] = str(jdata[key]['alfresco-jmxuser'])
                if 'alfresco-jmxpassword' in jdata[key]:
                    newconfig['default']['alfresco-jmxpassword'] = str(jdata[key]['alfresco-jmxpassword'])
                if 'alfresco-jmxaddress' in jdata[key]:
                    newconfig['default']['alfresco-jmxaddress'] = str(jdata[key]['alfresco-jmxaddress'])
                if 'alfresco-jmxport' in jdata[key]:
                    newconfig['default']['alfresco-jmxport'] = str(jdata[key]['alfresco-jmxport'])
                if 'alfresco-jmxpath' in jdata[key]:
                    newconfig['default']['alfresco-jmxpath'] = str(jdata[key]['alfresco-jmxpath'])
                if 'alfresco-jmxquery' in jdata[key]:
                    newconfig['default']['alfresco-jmxquery'] = str(jdata[key]['alfresco-jmxquery'])
                if 'alfresco-javapath' in jdata[key]:
                    newconfig['default']['alfresco-javapath'] = str(jdata[key]['alfresco-javapath'])
                
                if 'customchecks' in jdata[key]:
                    if jdata[key]['customchecks'] not in (1, "1", "true", "True", 0, "0", "false", "False"):
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
                        print_verbose("Update agent configuration ...", False)
                        agent_log.info("Update agent configuration ...")
                        newconfig.write(configfile)
                else:
                    print_verbose("No valid configuration path found", False)
                    agent_log.error("No valid configuration path found")
            
            elif key == 'config' and not file_readable(configpath):
                print_verbose("Agent configuration file not readable", False)
                agent_log.error("Agent configuration file not readable")
            
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
                        print_verbose("Update customchecks configuration ...", False)
                        agent_log.info("Update customchecks configuration ...")
                        newcustomchecks.write(configfile)
                else:
                    print_verbose("No valid customchecks configuration path found", False)
                    agent_log.error("No valid customchecks configuration path found")
            
            elif key == 'customchecks' and not file_readable(config['default']['customchecks']):
                print_verbose("Customchecks configuration file not readable", False)
                agent_log.error("Customchecks configuration file not readable")
            
        load_main_processing()
        
    except Exception as e:
        print_verbose("An error occurred while processing the new configuration", True)
        agent_log.error("An error occurred while processing the new configuration")
        agent_log.exception(e)
        
        if stacktrace:
            traceback.print_exc()
            print(e)
            

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    daemon_threads = True

class AgentWebserver(BaseHTTPRequestHandler):
    
    """Webserver class

    Parameters
    ----------
    BaseHTTPRequestHandler
        BaseHTTPRequestHandler

    """

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
        """Returns new csr

        Calls create_new_csr()

        Returns
        -------
        FILETYPE_PEM
            Certificate request (csr) in FILETYPE_PEM format.

        """
        return create_new_csr()

    
    def build_json_config(self):
        """Build / Prepare config for a JSON object

        Build and returns the current configuration as object (dict).

        Returns
        -------
        data
            Dictionary object with the current configuration

        """
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

            del cached_check_data
        except:
            
            if stacktrace:
                traceback.print_exc()
                
                
    def _process_post_data(self, data):
        executor = futures.ThreadPoolExecutor(max_workers=1)
        returnMessage = {}
        returnMessage['success'] = False
        
        if self.path == "/config" and config['default']['config-update-mode'] in (1, "1", "true", "True", True):
            executor.submit(check_update_data, data)
            returnMessage['success'] = True
        
        elif self.path == "/updateCrt" and autossl:
            permanent_webserver_thread(update_crt_files, (data,))
            returnMessage['success'] = True

        self._set_headers()
        self.wfile.write(json.dumps(returnMessage).encode())
    
    
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
                self._process_post_data(data=self.rfile.read(int(self.headers['Content-Length'])))

        except:
            print_verbose('Caught something in do_POST', True)
            if stacktrace:
                traceback.print_exc()
                
    
    def log_message(self, format, *args):
        agent_log.info("%s - - [%s] %s" % (self.address_string(),self.log_date_time_string(),format%args))
        if verbose:
            print("%s - - [%s] %s" % (self.address_string(),self.log_date_time_string(),format%args))
        return

    


def check_systemd_services(timeout):
    """Function that starts as a thread to run the systemd services check
    
    Linux only! (beta)
    
    Function that runs a (systemctl) command (as python subprocess) to get a status result for each registered systemd service.

    Parameters
    ----------
    timeout
        Command timeout in seconds

    """
    global systemd_services_data
    global cached_check_data
    
    agent_log.info('Start systemd services check with timeout of %ss at %s' % (str(timeout), str(round(time.time()))))
    if verbose:
        print('Start systemd services check with timeout of %ss at %s' % (str(timeout), str(round(time.time()))))
    
    systemd_services_data['running'] = "true"
    
    systemd_services = []
    if system == 'linux' and config['default']['systemdservices'] in (1, "1", "true", "True"):
        systemd_stats_command = "systemctl list-units --type=service --all --no-legend --no-pager --no-ask-password"
        try:
            tmp_systemd_stats_result = ''
            p = subprocess.Popen(systemd_stats_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            
            try:
                stdout, stderr = p.communicate(timeout=3)
                p.poll()
                if stdout:
                    tmp_systemd_stats_result = tmp_systemd_stats_result + stdout.decode()
                if stderr:
                    stderr = stderr.decode()

                systemd_services_data['error'] = None if str(stderr) == 'None' else str(stderr)
                systemd_services_data['returncode'] = p.returncode
            except subprocess.TimeoutExpired:
                print_verbose('systemd status check timed out', False)
                p.kill()    #not needed; just to be sure
                systemd_services_data['result'] = None
                systemd_services_data['error'] = 'systemd status check timeout after 3 seconds'
                systemd_services_data['returncode'] = 124
        
            if tmp_systemd_stats_result != '' and systemd_services_data['returncode'] == 0:
                results = tmp_systemd_stats_result.split('\n')
                for result in results:
                    if result.strip() != "":
                        try:
                            result_array_unsorted = result.strip().split(' ')
                            result_array_tmp = []
                            result_array = []
                            for i in range(len(result_array_unsorted)):
                                if str(result_array_unsorted[i]) != "":
                                    result_array_tmp.append(result_array_unsorted[i])
                                
                            for i in range(4):
                                result_array.append(result_array_tmp[0])
                                del result_array_tmp[0]
                                
                            service_description = ''
                            for i in range(len(result_array_tmp)):
                                service_description = service_description + result_array_tmp[i] + ' '
                            
                            tmp_dict = {}
                            tmp_dict['unit'] = result_array[0]
                            tmp_dict['load'] = result_array[1]
                            tmp_dict['active'] = result_array[2]
                            tmp_dict['sub'] = result_array[3]
                            tmp_dict['desc'] = service_description.strip()
                            systemd_services.append(tmp_dict)
                        except:
                            print_verbose("An error occured while processing the systemd check output!", True)
                            agent_log.error("An error occured while processing the systemd check output!")
                            
                            if stacktrace:
                                traceback.print_exc()
                                
                
                systemd_services_data['result'] = systemd_services
                systemd_services_data['last_updated_timestamp'] = round(time.time())
                systemd_services_data['last_updated'] = time.ctime()
            
        except:
            print_verbose('An error occured while running the systemd status check!', True)
            agent_log.error('An error occured while running the systemd status check!')
            
            if stacktrace:
                traceback.print_exc()
                
    
    del systemd_services_data['running']
    if len(systemd_services_data) > 0:
        cached_check_data['systemd_services'] = systemd_services_data
    print_verbose('Systemd services check finished', False)
    agent_log.info('Systemd services check finished')
    
    
def check_alfresco_stats():
    """Function that starts as a thread to run the alfresco stats check
        
    Function that a jmx query to get a status result for a configured alfresco enterprise instance.

    """
    global alfresco_stats_data
    global cached_check_data
    
    agent_log.info('Start alfresco stats check at %s' % (str(round(time.time()))))
    if verbose:
        print('Start alfresco stats check at %s' % (str(round(time.time()))))
        
    
    alfresco_stats_data['running'] = "true"
    
    
    alfrescostats = []
    if jmx_import_successfull and 'alfrescostats' in config['default'] and config['default']['alfrescostats'] in (1, "1", "true", "True", True):
        if file_readable(config['default']['alfresco-javapath']):
            try:
                uri = ("%s:%s%s" % (config['default']['alfresco-jmxaddress'], config['default']['alfresco-jmxport'], config['default']['alfresco-jmxpath']))
                alfresco_jmxConnection = JMXConnection("service:jmx:rmi:///jndi/rmi://" + uri, config['default']['alfresco-jmxuser'], config['default']['alfresco-jmxpassword'], config['default']['alfresco-javapath'])
                alfresco_jmxQueryString = "java.lang:type=Memory/HeapMemoryUsage/used;java.lang:type=OperatingSystem/SystemLoadAverage;java.lang:type=Threading/ThreadCount;Alfresco:Name=Runtime/TotalMemory;Alfresco:Name=Runtime/FreeMemory;Alfresco:Name=Runtime/MaxMemory;Alfresco:Name=WorkflowInformation/NumberOfActivitiWorkflowInstances;Alfresco:Name=WorkflowInformation/NumberOfActivitiTaskInstances;Alfresco:Name=Authority/NumberOfGroups;Alfresco:Name=Authority/NumberOfUsers;Alfresco:Name=RepoServerMgmt/UserCountNonExpired;Alfresco:Name=ConnectionPool/NumActive;Alfresco:Name=License/RemainingDays;Alfresco:Name=License/CurrentUsers;Alfresco:Name=License/MaxUsers"
                
                if 'alfresco-jmxquery' in config and config['default']['alfresco-jmxquery'] != "":
                    print("customquerx")
                    agent_log.info("customquerx")
                    alfresco_jmxQueryString = config['default']['alfresco-jmxquery']
                
                alfresco_jmxQuery = [JMXQuery(alfresco_jmxQueryString)]
                alfresco_metrics = alfresco_jmxConnection.query(alfresco_jmxQuery)
                
                for metric in alfresco_metrics:
                    alfrescostats.append({
                        'name': metric.to_query_string(),
                        'value': str(metric.value),
                        'value_type': str(metric.value_type)
                    })
                
            except subprocess.CalledProcessError as e:
                alfrescostats = "An error occured during alfresco stats check while connecting to jmx!"
                print_verbose(alfrescostats, True)
                agent_log.error(alfrescostats)
                
                if stacktrace:
                    traceback.print_exc()
                    
            except:
                alfrescostats = "An error occured during alfresco stats check!"
                print_verbose(alfrescostats, True)
                agent_log.error(alfrescostats)
                
                if stacktrace:
                    traceback.print_exc()
            
        else:
            alfrescostats = 'JAVA instance not found! (' + config['default']['alfresco-javapath'] + ')';
    
    alfresco_stats_data['result'] = alfrescostats
    cached_check_data['alfrescostats'] = alfrescostats
    print_verbose('Alfresco stats check finished', False)
    agent_log.info('Alfresco stats check finished')
    del alfresco_stats_data['running']


def check_qemu_stats(timeout):
    """Function that starts as a thread to run the qemu status check
    
    Linux only! (beta)
    
    Function that runs a (ps) command (as python subprocess) to get a status result for each running qemu (kvm) virtual machine.

    Parameters
    ----------
    timeout
        Command timeout in seconds

    """
    global qemu_stats_data
    global cached_check_data
    
    agent_log.info('Start qemu status check with timeout of %ss at %s' % (str(timeout), str(round(time.time()))))
    if verbose:
        print('Start qemu status check with timeout of %ss at %s' % (str(timeout), str(round(time.time()))))
        
    
    tmp_qemu_stats_result = None
    qemu_stats_data['running'] = "true"
    
    # regex source: https://gist.github.com/kitschysynq/867caebec581cee4c44c764b4dd2bde7
    # qemu_command = "ps -ef | awk -e '/qemu/ && !/awk/ && !/openitcockpit-agent/' | sed -e 's/[^/]*/\n/' -e 's/ -/\n\t-/g'" # customized (without secure character escape)
    qemu_command = "ps -ef | gawk -e '/qemu/ && !/gawk/ && !/openitcockpit-agent/' | sed -e 's/[^/]*/\\n/' -e 's/ -/\\n\\t-/g'" # customized
    
    try:
        p = subprocess.Popen(qemu_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        try:
            stdout, stderr = p.communicate(timeout=int(timeout))
            p.poll()
            if stdout:
                stdout = stdout.decode()
            if stderr:
                stderr = stderr.decode()
            tmp_qemu_stats_result = str(stdout)
            qemu_stats_data['error'] = None if str(stderr) == 'None' else str(stderr)
            qemu_stats_data['returncode'] = p.returncode
        except subprocess.TimeoutExpired:
            print_verbose('Qemu status check timed out', False)
            agent_log.warning('Qemu status check timed out')
            p.kill()    #not needed; just to be sure
            qemu_stats_data['result'] = None
            qemu_stats_data['error'] = 'Qemu status check timeout after ' + str(timeout) + ' seconds'
            qemu_stats_data['returncode'] = 124
    
    except:
        print_verbose('An error occured while running the qemu status check!', True)
        agent_log.error('An error occured while running the qemu status check!')
        
        if stacktrace:
            traceback.print_exc()
            
    
    if tmp_qemu_stats_result is not None and qemu_stats_data['returncode'] == 0:
        ordered_results = []
        qemuresults = tmp_qemu_stats_result.split('\n\n')
        for machine in qemuresults:
            machine_data = {}
            for line in machine.split('\n'):
                line = line.strip()
                
                if line.split(' ')[0].strip().startswith('-'):
                    option = line.split(' ')[0].strip()
                    arrayoption = option[1:]
                    if arrayoption not in machine_data:
                        machine_data[arrayoption] = line.split(option)[1].strip()
                    else:
                        if isinstance(machine_data[arrayoption], list):
                            machine_data[arrayoption].append(line.split(option)[1].strip())
                        else:
                            current_content = machine_data[arrayoption]
                            machine_data[arrayoption] = []
                            machine_data[arrayoption].append(current_content)
                            machine_data[arrayoption].append(line.split(option)[1].strip())
                
            ordered_results.append(machine_data)
        
        qemu_stats_data['result'] = ordered_results
        qemu_stats_data['last_updated_timestamp'] = round(time.time())
        qemu_stats_data['last_updated'] = time.ctime()
        
    elif qemu_stats_data['error'] is None and tmp_qemu_stats_result != "":
        if qemu_stats_data['returncode'] == 1 and tmp_qemu_stats_result.startswith('sed:'):
            qemu_stats_data['error'] = "No qemu machines running"
        else:
            qemu_stats_data['error'] = tmp_qemu_stats_result
    
    if len(qemu_stats_data) > 0:
        cached_check_data['qemustats'] = qemu_stats_data
    print_verbose('Qemu status check finished', False)
    agent_log.info('Qemu status check finished')
    del qemu_stats_data['running']


def check_docker_stats(timeout):
    """Function that starts as a thread to run the docker status check
    
    Linux only!
    
    Function that runs a docker command (as python subprocess) to get a status result for each running docker container.

    Parameters
    ----------
    timeout
        Command timeout in seconds

    """
    global docker_stats_data
    global cached_check_data
    
    print('Start docker status check with timeout of %ss at %s' % (str(timeout), str(round(time.time()))))
    if verbose:
        agent_log.info('Start docker status check with timeout of %ss at %s' % (str(timeout), str(round(time.time()))))
    
    tmp_docker_stats_result = ''
    docker_stats_data['running'] = "true"
    
    docker_stats_command = 'docker stats --no-stream --format "stats;{{.ID}};{{.Name}};{{.CPUPerc}};{{.MemUsage}};{{.MemPerc}};{{.NetIO}};{{.BlockIO}};{{.PIDs}}"'
    if system == 'windows':
        docker_stats_command = 'docker stats --no-stream --format "stats;{{.ID}};{{.Name}};{{.CPUPerc}};{{.MemUsage}};;{{.NetIO}};{{.BlockIO}};"'   #fill not existing 'MemPerc' and 'PIDs' with empty ; separated value
    docker_container_list_command = 'docker container list -a -s --format "cl;{{.ID}};{{.Status}};{{.Size}};{{.Image}};{{.RunningFor}};{{.Names}}"'

    try:
        p = subprocess.Popen(docker_stats_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p2 = subprocess.Popen(docker_container_list_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        try:
            stdout, stderr = p.communicate(timeout=int(timeout))
            stdout2, stderr2 = p2.communicate(timeout=int(timeout))
            p.poll()
            p2.poll()
            if stdout:
                tmp_docker_stats_result = tmp_docker_stats_result + stdout.decode()
            if stdout2:
                tmp_docker_stats_result = tmp_docker_stats_result + stdout2.decode()
            if stderr:
                stderr = stderr.decode()
            if stderr2:
                stderr2 = stderr2.decode()

            docker_stats_data['error'] = None if str(stderr) == 'None' else str(stderr)
            docker_stats_data['error'] = None if str(stderr) == 'None' and str(stderr2) == 'None' else str(stderr2)
            docker_stats_data['returncode'] = p.returncode
        except subprocess.TimeoutExpired:
            print_verbose('Docker status check timed out', False)
            agent_log.error('Docker status check timed out')
            p.kill()    #not needed; just to be sure
            p2.kill()
            docker_stats_data['result'] = None
            docker_stats_data['error'] = 'Docker status check timeout after ' + str(timeout) + ' seconds'
            docker_stats_data['returncode'] = 124
    
    except:
        print_verbose('An error occured while running the docker status check!', True)
        agent_log.error('An error occured while running the docker status check!')
        
        if stacktrace:
            traceback.print_exc()
            
    
    if tmp_docker_stats_result != '' and docker_stats_data['returncode'] == 0:
        results = tmp_docker_stats_result.split('\n')
        sorted_data = []
        sorted_stats_data = []
        sorted_cl_data = []
        for result in results:
            if result.strip() != "":
                try:
                    result_array = result.strip().split(';')
                    tmp_dict = {}
                    if result_array[0] == 'stats':
                        tmp_dict['id'] = result_array[1]
                        tmp_dict['name'] = result_array[2]
                        tmp_dict['cpu_percent'] = result_array[3]
                        tmp_dict['memory_usage'] = result_array[4]
                        tmp_dict['memory_percent'] = result_array[5]
                        tmp_dict['net_io'] = result_array[6]
                        tmp_dict['block_io'] = result_array[7]
                        tmp_dict['pids'] = result_array[8]
                        sorted_stats_data.append(tmp_dict)
                    if result_array[0] == 'cl':
                        tmp_dict['id'] = result_array[1]
                        tmp_dict['status'] = result_array[2]
                        tmp_dict['size'] = result_array[3]
                        tmp_dict['image'] = result_array[4]
                        tmp_dict['created'] = result_array[5]
                        tmp_dict['name'] = result_array[6]
                        sorted_cl_data.append(tmp_dict)
                except:
                    print_verbose("An error occured while processing the docker check output! Seems like there are no docker containers.", True)
                    agent_log.error("An error occured while processing the docker check output! Seems like there are no docker containers.")
                    
                    if stacktrace:
                        traceback.print_exc()

        for cl_data in sorted_cl_data:
            tmp_dict = cl_data

            for stats_data in sorted_stats_data:
                if stats_data['id'] == cl_data['id']:
                    tmp_dict['name'] = stats_data['name']
                    tmp_dict['cpu_percent'] = stats_data['cpu_percent']
                    tmp_dict['memory_usage'] = stats_data['memory_usage']
                    tmp_dict['memory_percent'] = stats_data['memory_percent']
                    tmp_dict['net_io'] = stats_data['net_io']
                    tmp_dict['block_io'] = stats_data['block_io']
                    tmp_dict['pids'] = stats_data['pids']
            sorted_data.append(tmp_dict)
    
        docker_stats_data['result'] = sorted_data
        docker_stats_data['last_updated_timestamp'] = round(time.time())
        docker_stats_data['last_updated'] = time.ctime()
    elif docker_stats_data['error'] is None and tmp_docker_stats_result != "":
        docker_stats_data['error'] = tmp_docker_stats_result
    
    if len(docker_stats_data) > 0:
        cached_check_data['dockerstats'] = docker_stats_data
    print_verbose('Docker status check finished', False)
    agent_log.info('Docker status check finished')
    del docker_stats_data['running']


def collect_data_for_cache(check_interval):
    """Function that starts as a thread to process the default checks
    
    Function to process the default checks with a given check interval.
    Starts the docker and qemu stats check threads (with timeout = check_interval) if configured.
    It also runs the daily certificate expiration check.

    Parameters
    ----------
    check_interval
        Time in seconds to wait before running the next default check

    """
    global permanent_check_thread_running
    global cached_check_data

    permanent_check_thread_running = True
    
    time.sleep(1)
    if check_interval <= 0:
        check_interval = 5
    check_interval_counter = check_interval
    cert_expiration_interval_counter = 0
    
    while not thread_stop_requested:
        if check_interval_counter >= check_interval:
            try:
                if autossl and cert_expiration_interval_counter >= 86400:   # approx. every day - time of run_default_checks()
                    executor = futures.ThreadPoolExecutor(max_workers=1)
                    executor.submit(check_auto_certificate)
                    cert_expiration_interval_counter = 0
            except:
                print_verbose_without_lock("Error while starting the regularly certificate expiration check!", True)
                agent_log.error("Error while starting the regularly certificate expiration check!")
                
                if stacktrace:
                    traceback.print_exc()
                    
            
            try:
                if config['default']['dockerstats'] in (1, "1", "true", "True") and 'running' not in docker_stats_data:
                    print('run dockerstats')
                    thread = Thread(target = check_docker_stats, args = (check_interval, ))
                    thread.start()
                    #thread.join()
                if jmx_import_successfull and 'alfrescostats' in config['default'] and config['default']['alfrescostats'] in (1, "1", "true", "True", True):
                    print('run alfrescostats')
                    thread = Thread(target = check_alfresco_stats)
                    thread.start()
                if system == 'linux':
                    if config['default']['qemustats'] in (1, "1", "true", "True") and 'running' not in qemu_stats_data:
                        print('run qemustats')
                        thread = Thread(target = check_qemu_stats, args = (check_interval, ))
                        thread.start()
                    if config['default']['systemdservices'] in (1, "1", "true", "True") and 'running' not in systemd_services_data:
                        print('run systemdservices')
                        thread = Thread(target = check_systemd_services, args = (check_interval, ))
                        thread.start()
                
                cached_check_data = run_default_checks()
            except:
                print_verbose_without_lock("Could not run default checks!", True)
                agent_log.error("Could not run default checks!")
                
                if stacktrace:
                    traceback.print_exc()
                    
            check_interval_counter = 0
        time.sleep(1)
        check_interval_counter += 1
        cert_expiration_interval_counter += 1
    
    permanent_check_thread_running = False
    print_verbose('Stopped permanent_check_thread', False)
    agent_log.info('Stopped permanent_check_thread')


def run_customcheck_command(check):
    """Function that starts as a thread (future) to process a custom check command
    
    Process a custom check command until a given timeout.
    The result will be added to the cached_customchecks_check_data object.
    
    process_customcheck_results() takes care of a may dying run_customcheck_command thread.

    Parameters
    ----------
    check
        Object containing the specific check data (name, command, timeout)

    """
    print_verbose('Start custom check "%s" with timeout %s at %s' % (str(check['name']), str(check['timeout']), str(round(time.time()))), False)
    agent_log.info('Start custom check "%s" with timeout %s at %s' % (str(check['name']), str(check['timeout']), str(round(time.time()))))
    cached_customchecks_check_data[check['name']]['running'] = "true"
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
            print_verbose('Custom check "%s" timed out' % (check['name']), False)
            agent_log.error('Custom check "%s" timed out' % (check['name']))
            p.kill()    #not needed; just to be sure
            cached_customchecks_check_data[check['name']]['result'] = None
            cached_customchecks_check_data[check['name']]['error'] = 'Command timeout after ' + str(check['timeout']) + ' seconds'
            cached_customchecks_check_data[check['name']]['returncode'] = 124
    
    except:
        print_verbose('An error occured while running the custom check "%s"!' % (check['name']), True)
        agent_log.error('An error occured while running the custom check "%s"!' % (check['name']))
        
        if stacktrace:
            traceback.print_exc()
    
    cached_customchecks_check_data[check['name']]['last_updated_timestamp'] = round(time.time())
    cached_customchecks_check_data[check['name']]['last_updated'] = time.ctime()
    del cached_customchecks_check_data[check['name']]['running']
    return True


def process_customcheck_results(future_checks):
    """Function that starts as a thread (future) to collect the custom check results
    
    Wait until all custom check threads finished and remove the running flag (that prevents an concurrent execution) if a thread had errors and does not return True.
    Overwrite the cached custom check check data with the new one(if there is was any result).

    Parameters
    ----------
    future_checks
        Object containing the running custom check threads (futures)

    """
    for future in futures.as_completed(future_checks):   #, timeout=10
        check = future_checks[future]
        try:
            if not future.result(): # if run_customcheck_command do not return True (exception/error)
                del cached_customchecks_check_data[check['name']]['running']
            print_verbose('Custom check "%s" stopped' % (check['name']), False)
            agent_log.info('Custom check "%s" stopped' % (check['name']))
        except:
            print_verbose('An error occured while checking custom check "%s" alive!' % (check['name']), True)
            agent_log.error('An error occured while checking custom check "%s" alive!' % (check['name']))
            
            if stacktrace:
                traceback.print_exc()
                
    
    if len(cached_customchecks_check_data) > 0:
        cached_check_data['customchecks'] = cached_customchecks_check_data


def collect_customchecks_data_for_cache(customchecks):
    """Function that starts as a thread to manage the custom checks 
    
    For each custom check an own thread (future) will (in a configured interval) be spawned to run the custom check command with a given timeout.

    Parameters
    ----------
    customchecks
        Configuration object that will be used to read the configured custom checks

    """
    global permanent_customchecks_check_thread_running
    permanent_customchecks_check_thread_running = True
    max_workers = 4
    if 'DEFAULT' in customchecks:
        if 'max_worker_threads' in customchecks['DEFAULT']:
            max_workers = int(customchecks['DEFAULT']['max_worker_threads'])
    if 'default' in customchecks:
        if 'max_worker_threads' in customchecks['default']:
            max_workers = int(customchecks['default']['max_worker_threads'])
            
    print_verbose('Start thread pool with max. %s workers' % (str(max_workers)), False)
    agent_log.info('Start thread pool with max. %s workers' % (str(max_workers)))
    
    executor = futures.ThreadPoolExecutor(max_workers=max_workers)
    
    while not thread_stop_requested:
        need_to_be_checked = []
        for check_name in customchecks:
            if check_name != 'DEFAULT' and check_name != 'default':
                if 'command' in customchecks[check_name] and customchecks[check_name]['command'] != '' and ('enabled' not in customchecks[check_name] or customchecks[check_name]['enabled'] in (1, "1", "true", "True", True)):
                    command = customchecks[check_name]['command']
                    interval = int(config['default']['interval'])
                    timeout = 60
                    
                    if customchecks[check_name]['interval']:
                        interval = int(customchecks[check_name]['interval'])
                    if customchecks[check_name]['timeout']:
                        timeout = int(customchecks[check_name]['timeout'])
                    
                    # if not yet executed, create set timestamp = 0
                    if check_name not in cached_customchecks_check_data:
                        cached_customchecks_check_data[check_name] = {
                            'last_updated': time.ctime(0),
                            'last_updated_timestamp': 0
                        }
                    
                    # execute if difference from timestamp of the last run and now greater or equal than interval
                    if (round(time.time()) - cached_customchecks_check_data[check_name]['last_updated_timestamp']) >= interval and 'running' not in cached_customchecks_check_data[check_name]:
                        check = {
                            'name': check_name,
                            'command': command,
                            'timeout': timeout
                        }
                        need_to_be_checked.append(check)
        
        # Start the load operations and mark each future with its URL
        if len(need_to_be_checked) > 0:
            future_checks = {
                executor.submit(run_customcheck_command, check): check for check in need_to_be_checked
            }
            executor.submit(process_customcheck_results, future_checks) #, timeout=biggestTimeout
        
        time.sleep(1)
    permanent_customchecks_check_thread_running = False
    print_verbose('Stopped permanent_customchecks_check_thread', False)
    agent_log.info('Stopped permanent_customchecks_check_thread')


def notify_oitc(oitc):
    """Function that starts as a thread to push check results to an openITCOCKPIT server
    
    Send a post request with a given interval to the configured openITCOCKPIT server containing the latest check results.
    If autossl is activated, add the sha512 checksum to the request, to validate the sender of the request.

    Parameters
    ----------
    oitc
        Configuration object that will be used to create the push connection

    """
    agent_log.info('Starting Push mode')

    global oitc_notification_thread_running
    global cached_check_data
    global cert_checksum
    
    time.sleep(1)
    if oitc['url'].strip() and oitc['apikey'].strip() and int(oitc['interval']):
        oitc_notification_thread_running = True
        noty_interval = int(oitc['interval'])
        if noty_interval <= 0:
            noty_interval = 5
        sleptSeconds = noty_interval - 4
        while not thread_stop_requested:
            if sleptSeconds < noty_interval:
                time.sleep(1)
                sleptSeconds = sleptSeconds + 1
                continue

            sleptSeconds = 0
            if len(cached_check_data) > 0:
                try:
                    data = {
                        'checkdata': json.dumps(cached_check_data),
                        'hostuuid': oitc['hostuuid']
                    }
                    if autossl and file_readable(config['default']['autossl-crt-file']):
                        if cert_checksum != '':
                            data['checksum'] = cert_checksum
                        else:
                            with open(config['default']['autossl-crt-file'], 'r') as f:
                                cert = f.read()
                                cert = cert.replace("\r\n", "\n")
                                sha512.update(cert.encode())
                                cert_checksum = sha512.hexdigest().upper()
                                data['checksum'] = cert_checksum
                    
                    headers = {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Authorization': 'X-OITC-API '+oitc['apikey'].strip(),
                    }

                    try:
                        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
                    except:
                        
                        if stacktrace:
                            traceback.print_exc()
                            
                    agent_log.info('Handing over check results')
                    agent_log.info(oitc['url'].strip())
                    response = requests.post(oitc['url'].strip() + '/agentconnector/updateCheckdata.json', data=data, headers=headers, verify=False)
                    agent_log.info(response)

                    if response.content.decode('utf-8').strip() != '':
                        responseData = json.loads(response.content.decode('utf-8'))
                        if autossl and 'new_ca' in responseData and 'ca_checksum' in responseData and responseData['new_ca'] in (1, "1", "true", "True", True) and file_readable(config['default']['autossl-ca-file']):

                            with open(config['default']['autossl-ca-file'], 'r') as f:
                                ca = f.read()
                                ca = ca.replace("\r\n", "\n")
                                sha512.update(ca.encode())
                                ca_checksum = sha512.hexdigest().upper()

                                if responseData['new_ca'] == ca_checksum:   # validates, that new ca request comes from old ca server
                                    doNotWaitForReturnExecutor = futures.ThreadPoolExecutor(max_workers=1)
                                    doNotWaitForReturnExecutor.submit(pull_crt_from_server, True)
                    
                    #if verbose:
                    #    print(response.status_code)
                    #    print(response.content.decode('utf-8'))

                except:
                    print_verbose('An error occured while trying to notify your configured openITCOCKPIT instance!', True)
                    agent_log.error('An error occured while trying to notify your configured openITCOCKPIT instance!')
                    
                    if stacktrace:
                        traceback.print_exc()
                        
    oitc_notification_thread_running = False
    print_verbose('Stopped oitc_notification_thread', False)
    agent_log.info('Stopped oitc_notification_thread')


def process_webserver(enableSSL=False):
    """Function that starts as a thread to process the webserver
    
    Starts a http webserver at the configured address and port.
    If enableSSL is specified a custom certificate will be used to start a https webserver.
    If the global autossl is enabled and the needed files are readable the automatically generated certificate will be used to start a https webserver.
    
    Restarts the "real" webserver application if it dies.

    Parameters
    ----------
    enableSSL
        Boolean to specify if ssl with a custom certificate will be used or not

    """
    global permanent_webserver_thread_running

    if permanent_webserver_thread_running:
        return False

    permanent_webserver_thread_running = True
    
    protocol = 'http'
    if config['default']['address'] == "":
        config['default']['address'] = "0.0.0.0"
        
    agent_log.info('Starting webserver ...')
    server_address = (config['default']['address'], int(config['default']['port']))
    httpd = ThreadedHTTPServer(server_address, AgentWebserver)
    
    
    if enableSSL:
        agent_log.info('SSL Enabled')
        protocol = 'https'
        httpd.socket = ssl.wrap_socket(httpd.socket, keyfile=config['default']['keyfile'], certfile=config['default']['certfile'], server_side=True)
    elif autossl and file_readable(config['default']['autossl-key-file']) and file_readable(config['default']['autossl-crt-file']) and file_readable(config['default']['autossl-ca-file']):
        agent_log.info('SSL with custom certificate enabled')
        protocol = 'https'
        httpd.socket = ssl.wrap_socket(httpd.socket, keyfile=config['default']['autossl-key-file'], certfile=config['default']['autossl-crt-file'], server_side=True, cert_reqs = ssl.CERT_REQUIRED, ca_certs = config['default']['autossl-ca-file'])
        
    
    print_verbose("Server started at %s://%s:%s with a check interval of %d seconds" % (protocol, config['default']['address'], str(config['default']['port']), int(config['default']['interval'])), False)
    agent_log.info("Server started at %s://%s:%s with a check interval of %d seconds" % (protocol, config['default']['address'], str(config['default']['port']), int(config['default']['interval'])))

  
    while not thread_stop_requested and not webserver_stop_requested:
        try:
            httpd.handle_request()
        except:
            print_verbose('Webserver died, try to restart ...', False)
            agent_log.error('Webserver died, try to restart ...')
        sleep(1)
    del httpd
    permanent_webserver_thread_running = False
    print_verbose('Stopped permanent_webserver_thread', False)
    agent_log.info('Stopped permanent_webserver_thread')


def restart_webserver():
    """Function to restart the webserver
    
    Tries to stop the and start the webserver thred again.
    Therefore a fake GET request is made, calling the function fake_webserver_request().
    
    If the web server has not been run before, it will not start!

    """
    agent_log.info('Restarting webserver')
    global webserver_stop_requested
    global wait_and_check_auto_certificate_thread_stop_requested
    
    tmp_permanent_webserver_thread_running = permanent_webserver_thread_running
    time.sleep(2)
    
    if initialized:
        webserver_stop_requested = True
        wait_and_check_auto_certificate_thread_stop_requested = True
        
        try:
            agent_log.info('Check webserver is alive')
            fake_webserver_request()
        except:
            agent_log.info('Webserver is not alive')
            if stacktrace:
                traceback.print_exc()
                
        
        while webserver_stop_requested:
            if permanent_webserver_thread_running:
                sleep(1)
            else:
                webserver_stop_requested = False
    
    if tmp_permanent_webserver_thread_running:
        permanent_webserver_thread(process_webserver, (enableSSL,))
        agent_log.info('Webserver thread restarted')


def create_new_csr():
    """Function that creates a new certificate request (csr)

    Creates a RSA (4096) certificate request.
    The hostname is config['oitc']['hostuuid'] + '.agent.oitc'.
    
    Writes csr in the default or custom autossl-csr-file.
    
    Writes certificate key in the default or custom autossl-key-file.
    

    Returns
    -------
    FILETYPE_PEM
        Returns a pem object (FILETYPE_PEM) on success

    """
    global ssl_csr
    
    try:
        
        # ECC (not working yet)
        # 
        # from Crypto.PublicKey import ECC
        # 
        # key = ECC.generate(curve='prime256v1')
        # req = X509Req()
        # req.get_subject().CN = config['oitc']['hostuuid']+'.agent.oitc'
        # publicKey = key.public_key().export_key(format='PEM', compress=False)
        # privateKey = key.export_key(format='PEM', compress=False, use_pkcs8=True)
        # 
        # pubdict = {}
        # pubdict['_only_public'] = publicKey
        # req.sign(publicKey, 'sha384')
        
        agent_log.info('Creating new csr')

        # create public/private key
        key = PKey()
        key.generate_key(TYPE_RSA, 4096)
    
        # Generate CSR
        req = X509Req()
        req.get_subject().CN = config['oitc']['hostuuid']+'.agent.oitc'
        
        
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
                        print_verbose('An error occured while creating the ssl files containing folders', True)
                        agent_log.error('An error occured while creating the ssl files containing folders')
                        if stacktrace:
                            raise

    
        csr = dump_certificate_request(FILETYPE_PEM, req)
        with open(config['default']['autossl-csr-file'], 'wb+') as f:
            f.write(csr)
        with open(config['default']['autossl-key-file'], 'wb+') as f:
            f.write(dump_privatekey(FILETYPE_PEM, key))
        ssl_csr = csr
            
        agent_log.info('csr file written')
    except:
        print_verbose('An error occured while creating a new certificate request (csr)', True)
        agent_log.error('An error occured while creating a new certificate request (csr)')
        
        if stacktrace:
            traceback.print_exc()
            
    return csr


def pull_crt_from_server(renew=False):
    """Function to pull a new certificate using a csr

    This function tries to pull a new certificate from the configured openITCOCKPIT Server.
    Therefore a new certificate request (csr) is needed and create_new_csr() will be called.
    The request with the csr should return the new client (and the CA) certificate.

    If the agent is not known and not yet trusted by the openITCOCKPIT Server the function will be executed again in 10 minutes.
    Therefore the function wait_and_check_auto_certificate(600) will be called as new thread (future).
    
    If the agent is not yet trusted by the openITCOCKPIT Server a manual confirmation in the openITCOCKPIT frontend is needed!

    If an existing certificate expired, a sha512 checksum has to be sent with the request to the openITCOCKPIT Server.
    With that checksum the server can validate, that the request was sent from a trusted agent (that has access to the old certificate).

    Returns
    -------
    bool
        True if successful, False otherwise.

    """
    global cert_checksum
    
    agent_log.info('Pulling csr file from Server')

    if certificate_check_lock.locked():
        print_verbose('Function to pull a new certificate is locked!', False)
        agent_log.warning('Function to pull a new certificate is locked!')
        return False
    
    with certificate_check_lock:
        if config['oitc']['url'] and config['oitc']['url'] != "" and config['oitc']['apikey'] and config['oitc']['apikey'] != "" and config['oitc']['hostuuid'] and config['oitc']['hostuuid'] != "":
            try:
                csr = create_new_csr()

                data = {
                    'csr': csr.decode(),
                    'hostuuid': config['oitc']['hostuuid']
                }
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Authorization': 'X-OITC-API '+config['oitc']['apikey'].strip(),
                }
                if renew:
                    with open(config['default']['autossl-crt-file'], 'r') as f:
                        cert = f.read()
                        cert = cert.replace("\r\n", "\n")
                        sha512.update(cert.encode())
                        data['checksum'] = sha512.hexdigest().upper()

                try:
                    requests.packages.urllib3.disable_warnings()
                except:
                    
                    if stacktrace:
                        traceback.print_exc()
                        

                response = requests.post(config['oitc']['url'].strip() + '/agentconnector/certificate.json', data=data, headers=headers, verify=False)
                if response.content.decode('utf-8').strip() != '':
                    jdata = json.loads(response.content.decode('utf-8'))

                    if 'checksum_missing' in jdata:
                        print_verbose('Agent certificate already generated. May be hijacked?', False)
                        print_verbose('Add old certificate checksum to request or recreate Agent in openITCOCKPIT.', False)
                        agent_log.warning('Agent certificate already generated. May be hijacked?')
                        agent_log.warning('Add old certificate checksum to request or recreate Agent in openITCOCKPIT.')

                    if 'unknown' in jdata:
                        print_verbose('Untrusted agent! Try again in 1 minute to get a certificate from the server.', False)
                        agent_log.warning('Untrusted agent! Try again in 1 minute to get a certificate from the server.')
                        executor = futures.ThreadPoolExecutor(max_workers=1)
                        executor.submit(wait_and_check_auto_certificate, 60)

                    if 'signed' in jdata and 'ca' in jdata:
                        with open(config['default']['autossl-crt-file'], 'w+') as f:
                            f.write(jdata['signed'])
                            sha512.update(jdata['signed'].encode())
                            cert_checksum = sha512.hexdigest().upper()
                        with open(config['default']['autossl-ca-file'], 'w+') as f:
                            f.write(jdata['ca'])

                        restart_webserver()

                        print_verbose('Signed certificate updated successfully', False)
                        agent_log.info('Signed certificate updated successfully')
                        return True
            except:
                print_verbose('An error occurred during autossl certificate renew process', True)
                agent_log.error('An error occurred during autossl certificate renew process')
                
                if stacktrace:
                    traceback.print_exc()
                    
    
    return False


def wait_and_check_auto_certificate(seconds):
    """Function to wait until the next automatic certificate check

    Parameters
    ----------
    seconds
        Time in seconds to wait before running the next automatic certificate check

    """
    global wait_and_check_auto_certificate_thread_stop_requested
    
    print_verbose('Started wait_and_check_auto_certificate', False)
    agent_log.info('Started wait_and_check_auto_certificate')

    if autossl:
        i = 0
        while i < seconds and not wait_and_check_auto_certificate_thread_stop_requested and not thread_stop_requested:
            time.sleep(1)
            i = i + 1
        
        if not wait_and_check_auto_certificate_thread_stop_requested:
            doNotWaitForReturnExecutor = futures.ThreadPoolExecutor(max_workers=1)
            doNotWaitForReturnExecutor.submit(check_auto_certificate)
    wait_and_check_auto_certificate_thread_stop_requested = False
    print_verbose('Finished wait_and_check_auto_certificate', False)
    agent_log.info('Finished wait_and_check_auto_certificate')


def check_auto_certificate():
    """Function to check the automatically generated certificate

    This function checks if the automatically generated certificate is installed and will otherwise trigger the download.
    Otherwise it checks if the certificate will expire soon.
        
    """
    agent_log.info('Check Certificate')
    requestNewCertificate = False
    if not file_readable(config['default']['autossl-crt-file']):
        agent_log.warning('Cannot read crt file')
        pull_crt_from_server()
    if file_readable(config['default']['autossl-crt-file']):    # repeat condition because pull_crt_from_server could fail
        agent_log.info('crt file found and readable')
        with open(config['default']['autossl-crt-file'], 'r') as f:
            cert = f.read()
            x509 = load_certificate(FILETYPE_PEM, cert)
            x509info = x509.get_notAfter()
            exp_day = x509info[6:8].decode('utf-8')
            exp_month = x509info[4:6].decode('utf-8')
            exp_year = x509info[:4].decode('utf-8')
            exp_date = str(exp_day) + "-" + str(exp_month) + "-" + str(exp_year)
            
            print_verbose("SSL Certificate expires in %s on %s (DD-MM-YYYY)" % (str(datetime.date(int(exp_year), int(exp_month), int(exp_day)) - datetime.datetime.now().date()).split(',')[0], exp_date), False)
            agent_log.info("SSL Certificate expires in %s on %s (DD-MM-YYYY)" % (str(datetime.date(int(exp_year), int(exp_month), int(exp_day)) - datetime.datetime.now().date()).split(',')[0], exp_date))
            
            if datetime.date(int(exp_year), int(exp_month), int(exp_day)) - datetime.datetime.now().date() <= datetime.timedelta(days_until_cert_warning):
                print_verbose('SSL Certificate will expire soon. Try to create a new one automatically ...', False)
                agent_log.warning('SSL Certificate will expire soon. Try to create a new one automatically ...')
                requestNewCertificate = True
    
    if file_readable(config['default']['autossl-ca-file']):
        agent_log.info('ca file found and readable')
        with open(config['default']['autossl-ca-file'], 'r') as f:
            ca = f.read()
            x509 = load_certificate(FILETYPE_PEM, ca)
            x509info = x509.get_notAfter()
            exp_day = x509info[6:8].decode('utf-8')
            exp_month = x509info[4:6].decode('utf-8')
            exp_year = x509info[:4].decode('utf-8')
            exp_date = str(exp_day) + "-" + str(exp_month) + "-" + str(exp_year)
            
            if datetime.date(int(exp_year), int(exp_month), int(exp_day)) - datetime.datetime.now().date() <= datetime.timedelta(days_until_ca_warning):
                print_verbose("CA Certificate expires in %s on %s (DD-MM-YYYY)" % (str(datetime.date(int(exp_year), int(exp_month), int(exp_day)) - datetime.datetime.now().date()).split(',')[0], exp_date), False)
                agent_log.info("CA Certificate expires in %s on %s (DD-MM-YYYY)" % (str(datetime.date(int(exp_year), int(exp_month), int(exp_day)) - datetime.datetime.now().date()).split(',')[0], exp_date))
                requestNewCertificate = True
                    
    if requestNewCertificate:
        agent_log.info('Try pulling new Certificate')
        if pull_crt_from_server(True):
            check_auto_certificate()


def print_help():
    """Function to print the help

    Prints the help text and the default configuration (file) options to cli.
        
    """
    print('usage: ./oitc_agent.py -v -i <check interval seconds> -p <port number> -a <ip address> -c <config path> --certfile <certfile path> --keyfile <keyfile path> --auth <user>:<password> --oitc-url <url> --oitc-apikey <api key> --oitc-interval <seconds>')
    print('\nOptions and arguments (overwrite options in config file):')
    print('-i --interval <seconds>                  : check interval in seconds')
    print('-p --port <number>                       : webserver port number')
    print('-a --address <ip address>                : webserver ip address')
    print('-c --config <config path>                : config file path')
    print('--config-update-mode                     : enable config update mode threw post request and /config to get current configuration')
    print('--temperature-fahrenheit                 : set temperature to fahrenheit if enabled (else use celsius)')
    print('--dockerstats                            : enable docker status check')
    print('--qemustats                              : enable qemu status check (linux only)')
    print('--no-cpustats                            : disable default cpu status check')
    print('--no-sensorstats                         : disable default sensor status check')
    print('--no-processstats                        : disable default process status check')
    print('--processstats-including-child-ids       : add process child ids to the default process status check (computationally intensive)')
    print('--no-netstats                            : disable default network status check')
    print('--no-diskstats                           : disable default disk status check')
    print('--no-netio                               : disable default network I/O calculation')
    print('--no-diskio                              : disable default disk I/O calculation')
    print('--no-winservices                         : disable default windows services status check (windows only)')
    print('--customchecks <file path>               : custom check config file path')
    print('--auth <user>:<password>                 : enable http basic auth')
    print('-v --verbose                             : enable verbose mode')
    print('-s --stacktrace                          : print stacktrace for possible exceptions')
    print('-h --help                                : print this help message and exit')
    print('\nAdd there parameters (all required) to enable transfer of check results to a openITCOCKPIT server:')
    print('--oitc-hostuuid <host uuid>              : host uuid from openITCOCKPIT')
    print('--oitc-url <url>                         : openITCOCKPIT url (https://demo.openitcockpit.io)')
    print('--oitc-apikey <api key>                  : openITCOCKPIT api key')
    print('--oitc-interval <seconds>                : transfer interval in seconds')
    print('\nAdd there parameters to enable ssl encrypted http(s) server:')
    print('--certfile <certfile path>               : /path/to/cert.pem')
    print('--keyfile <keyfile path>                 : /path/to/key.pem')
    print('--try-autossl                            : try to enable auto webserver ssl mode')
    print('--disable-autossl                        : disable auto webserver ssl mode (overwrite default)')
    print('\nFile paths used for autossl (default: /etc/openitcockpit-agent/... or C:\Program Files\openitcockpit-agent\...):')
    print('--autossl-folder <path>                  : /default/folder/for/ssl/files (use instead of the following four arguments)')
    print('--autossl-csr-file <path>                : /path/to/agent.csr')
    print('--autossl-crt-file <path>                : /path/to/agent.crt')
    print('--autossl-key-file <path>                : /path/to/agent.key')
    print('--autossl-ca-file <path>                 : /path/to/server_ca.crt')
    print('\nSample config file:')
    print(sample_config)
    print('\nSample config file for custom check commands:')
    print(sample_customcheck_config)


def load_configuration():
    """Function to load/reload all configuration options

    Read and merge the start parameters and options from the configuration files (if configured).
    
    Decides if ssl will be enabled or not.
        
    """
    global config
    global verbose
    global stacktrace
    global added_oitc_parameter
    global configpath
    global enableSSL
    global autossl
    global temperatureIsFahrenheit
    
    try:
        opts, args = getopt.getopt(sys.argv[1:],"h:i:p:a:c:vs",["interval=","port=","address=","config=","customchecks=","certfile=","keyfile=","auth=","oitc-hostuuid=","oitc-url=","oitc-apikey=","oitc-interval=","config-update-mode","temperature-fahrenheit","try-autossl","disable-autossl","autossl-folder","autossl-csr-file","autossl-crt-file","autossl-key-file","autossl-ca-file","dockerstats","qemustats","no-cpustats","no-sensorstats","no-processstats","processstats-including-child-ids","no-netstats","no-diskstats","no-netio","no-diskio","no-winservices","verbose","stacktrace","help"])
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
    
    if configpath != "":
        if file_readable(configpath):
            with open(configpath, 'r') as configfile:
                print_verbose('Load agent configuration file "%s"' % (configpath), False)
                agent_log.info('Load agent configuration file "%s"' % (configpath))
                config.read_file(configfile)
        else:
            with open(configpath, 'w') as configfile:
                print_verbose('Create new default agent configuration file "%s"' % (configpath), False)
                agent_log.info('Create new default agent configuration file "%s"' % (configpath))
                config.write(configfile)
    
    build_autossl_defaults()
    
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
        elif opt == "--try-autossl":
            config['default']['try-autossl'] = "true"
        elif opt == "--autossl-folder":
            config['default']['autossl-folder'] = str(arg)
        elif opt == "--autossl-csr-file":
            config['default']['autossl-csr-file'] = str(arg)
        elif opt == "--autossl-crt-file":
            config['default']['autossl-crt-file'] = str(arg)
        elif opt == "--autossl-key-file":
            config['default']['autossl-key-file'] = str(arg)
        elif opt == "--autossl-ca-file":
            config['default']['autossl-ca-file'] = str(arg)
        elif opt == "--auth":
            config['default']['auth'] = str(arg)
        elif opt in ("-v", "--verbose"):
            config['default']['verbose'] = "true"
        elif opt in ("-s", "--stacktrace"):
            config['default']['stacktrace'] = "true"
        elif opt == "--config-update-mode":
            config['default']['config-update-mode'] = "true"
        elif opt == "--temperature-fahrenheit":
            config['default']['temperature-fahrenheit'] = "true"
        elif opt == "--dockerstats":
            config['default']['dockerstats'] = "true"
        elif opt == "--qemustats":
            config['default']['qemustats'] = "true"
        elif opt == "--no-cpustats":
            config['default']['cpustats'] = "false"
        elif opt == "--no-sensorstats":
            config['default']['sensorstats'] = "false"
        elif opt == "--no-processstats":
            config['default']['processstats'] = "false"
        elif opt == "--processstats-including-child-ids":
            config['default']['processstats-including-child-ids'] = "true"
        elif opt == "--no-netstats":
            config['default']['netstats'] = "false"
        elif opt == "--no-diskstats":
            config['default']['diskstats'] = "false"
        elif opt == "--no-netio":
            config['default']['netio'] = "false"
        elif opt == "--no-diskio":
            config['default']['diskio'] = "false"
        elif opt == "--no-winservices":
            config['default']['winservices'] = "false"
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
    
    # loop again to consider default overwrite options
    for opt, arg in opts:
        if opt == "--disable-autossl":
            config['default']['try-autossl'] = "false"
            break
    
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
    
    if config['default']['autossl-folder'] != "":
        build_autossl_defaults()
    
    if config['default']['temperature-fahrenheit'] in (1, "1", "true", "True", True):
        temperatureIsFahrenheit = True
    else:
        temperatureIsFahrenheit = False
    
    if 'auth' in config['default'] and str(config['default']['auth']).strip():
        if not is_base64(config['default']['auth']):
            if isPython3:
                config['default']['auth'] = str(base64.b64encode(config['default']['auth'].encode()), "utf-8")
            else:
                config['default']['auth'] = str(base64.b64encode(config['default']['auth'].encode())).encode("utf-8")
    

    if config['default']['certfile'] != "" and config['default']['keyfile'] != "":
        try:
            if file_readable(config['default']['certfile']) and file_readable(config['default']['keyfile']):
                enableSSL = True
            else:
                agent_log.warning("Could not read certfile or keyfile\nFall back to default http server")
                if verbose:
                    print("Could not read certfile or keyfile\nFall back to default http server")
                
            
        except IOError:
            print_verbose("Could not read certfile or keyfile\nFall back to default http server", False)
            agent_log.warning("Could not read certfile or keyfile\nFall back to default http server")
    

def fake_webserver_request():
    """Runs a fake webserver request

    GET Request (using python requests lib) to let webserver thread continue.
    
    Usually called from reload_all() to notice the updated thread_stop_requested value.
        
    """
    protocol = 'http'
    if enableSSL:
        protocol = 'https'
    complete_address = protocol + '://' + config['default']['address'] + ':' + str(config['default']['port'])
    try:
        requests.get(complete_address, verify=False)
    except:
        pass
    

def reload_all():
    """Function to stop all thread and trigger the configuration reload

    Wait until all running threads are stopped and reset the global variables/objects.
    Call the load_configuration() function

    Returns
    -------
    bool
        True if successful (no failure expected)
        
    """
    global thread_stop_requested
    
    if initialized:
        thread_stop_requested = True
        
        try:
            fake_webserver_request()
        except:
            
            if stacktrace:
                traceback.print_exc()
                
        
        while thread_stop_requested:
            if update_crt_files_thread_running or permanent_check_thread_running or permanent_webserver_thread_running or oitc_notification_thread_running or permanent_customchecks_check_thread_running:
                sleep(1)
            else:
                thread_stop_requested = False
        reset_global_options()
    
    load_configuration()
    return True
    

def load_main_processing():
    """(Entry point) Function that initializes or reinitializes the agent on each call


    Starts ...

        - openITCOCKPIT Notification Thread (if enabled)
        - customchecks collector thread (if needed)
        - default check thread (including daily certificate expiration check)
        - webserver thread
        
    ... after (running check thread are stopped,) configuration is loaded and automatic certificate check is done.

    """
    global initialized
    
    while not reload_all():
        sleep(1)
    
    if autossl:
        check_auto_certificate()    #need to be called before initialized = True to prevent webserver thread restart
    
    initialized = True
    
    agent_log.info('Push mode enabled: %s',config['oitc']['enabled'])

    if 'oitc' in config and (config['oitc']['enabled'] in (1, "1", "true", "True", True) or added_oitc_parameter == 4):
        oitc_notification_thread(notify_oitc, (config['oitc'],))
    
    if config['default']['customchecks'] != "":
        if file_readable(config['default']['customchecks']):
            with open(config['default']['customchecks'], 'r') as customchecks_configfile:
                print_verbose('Load custom check configuration file "%s"' % (config['default']['customchecks']), False)
                agent_log.info('Load custom check configuration file "%s"' % (config['default']['customchecks']))
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
            time.sleep(0.1)
