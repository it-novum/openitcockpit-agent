#!/usr/bin/python

# supports python2.7 and python3.7
#
#
# start with parameters:    ./oitc_agent.py interval=30 port=3333 address=127.0.0.1
#
# Download & install python
#
# Windows:
#   Download & install current python version from https://www.python.org/downloads/windows/
#   open cmd and execute:   python.exe -m pip install psutil
#
# Debian:       
#       python3:
#               apt-get install python3 python3-psutil
#               pip3 uninstall psutil
#               pip3 install configparser
#       or
#       python2:
#               apt-get install python python-psutil
#               pip uninstall psutil
#               pip install futures configparser subprocess32
#
# Darwin:
#               brew install python3
#               pip3 install psutil configparser
#


import sys
import os
import io
from os import access, R_OK
from os.path import isfile
import getopt
import platform
import time
import json
import socket
import configparser
import traceback
import base64
from time import sleep
from subprocess import Popen, PIPE
import subprocess

isPython3 = False
system = 'linux'

if sys.platform == 'win32' or sys.platform == 'win64':
    system = 'windows'
if sys.platform == 'darwin' or (system == 'linux' and 'linux' not in sys.platform):
    system = 'darwin'

if (sys.version_info > (3, 0)):
    isPython3 = True
    import concurrent.futures as futures
    import urllib.request, urllib.parse
    from _thread import start_new_thread as permanent_check_thread
    from _thread import start_new_thread as oitc_notification_thread
    from _thread import start_new_thread as permanent_customchecks_check_thread
    from http.server import BaseHTTPRequestHandler, HTTPServer
else:
    from concurrent import futures
    import urllib
    import urllib2
    from thread import start_new_thread as permanent_check_thread
    from thread import start_new_thread as oitc_notification_thread
    from thread import start_new_thread as permanent_customchecks_check_thread
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    #import subprocess32
    import subprocess32 as subprocess
try:
    import psutil
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


agentVersion = "1.0.0"
enableSSL = False
cached_check_data = {}
cached_customchecks_check_data = {}
configpath = ""
customchecks_configpath = ""
verbose = False

sample_config = """
[default]
  interval = 30
  port = 3333
  address = 127.0.0.1
  certfile = 
  keyfile = 
  verbose = false
  # auth = user:pass
[oitc]
  url = 
  apikey = 
  interval = 60
  enabled = false
"""

sample_customcheck_config = """
[DEFAULT]
  # max_worker_threads should be increased with increasing number of custom checks
  # but consider: each thread needs (a bit) memory
  max_worker_threads = 4
[username]
  command = whoami
  interval = 30
  timeout = 5
  disabled = false
[uname]
  command = uname -a
  interval = 15
  timeout = 5
  disabled = true
"""

config = configparser.ConfigParser(allow_no_value=True)
customchecks = configparser.ConfigParser(allow_no_value=True)

class Collect:
    def getData(self):
        # CPU #
        cpuTotalPercentage = psutil.cpu_percent()
        cpuPercentage = psutil.cpu_percent(interval=0, percpu=True)

        cpu = psutil.cpu_times_percent(interval=0, percpu=False)
        cpuTotalPercentageDetailed = cpu._asdict()
        
        cpuPercentageDetailed = [dict(cpu._asdict()) for cpu in psutil.cpu_times_percent(interval=0, percpu=True)]
        

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
       

        diskIOTotal = psutil.disk_io_counters(perdisk=False)
        #diskIO = psutil.disk_io_counters(perdisk=True)
        
        diskIO = { disk: iops._asdict() for disk,iops in psutil.disk_io_counters(perdisk=True).items() }

        if hasattr(psutil, "pids"):
            pids = psutil.pids()
        else:
            pids = psutil.get_pid_list()

        #processes = [ psutil.Process(pid).as_dict() for pid in pids ]
        windows_services = []
        processes = []
        customchecks = {}
        
        for pid in pids:
            try:
                p = psutil.Process(pid)
                
                status = ""
                username = ""
                nice = None
                name = ""
                exe = ""
                cpu_percent = None
                memory_info = {}
                memory_percent = None
                num_fds = {}
                io_counters = {}
                open_files = ""
                
                try:
                    if callable(p.status):
                        status = p.status()
                    else:
                        status = p.status
                except:
                    if verbose:
                        traceback.print_exc()
                
                try:
                    if callable(p.username):
                        username = p.username()
                    else:
                        username = p.username
                except:
                    if verbose:
                        traceback.print_exc()
                    
                try:
                    if callable(p.nice):
                        nice = p.nice()
                    else:
                        nice = p.nice
                except:
                    if verbose:
                        traceback.print_exc()
                    
                try:
                    if callable(p.name):
                        name = p.name()
                    else:
                        name = p.name
                except:
                    if verbose:
                        traceback.print_exc()
                    
                try:
                    if callable(p.exe):
                        exe = p.exe()
                    else:
                        exe = p.exe
                except:
                    if verbose:
                        traceback.print_exc()
                    
                try:
                    if hasattr(p, "cpu_percent") and callable(p.cpu_percent):
                        cpu_percent = p.cpu_percent()
                    else:
                        cpu_percent = p.get_cpu_percent()
                except:
                    if verbose:
                        traceback.print_exc()
                        
                try:
                    if hasattr(p, "memory_info") and callable(p.memory_info):
                        memory_info = p.memory_info()
                    else:
                        memory_info = p.get_memory_info()
                except:
                    if verbose:
                        traceback.print_exc()
                    
                try:
                    if hasattr(p, "memory_percent") and callable(p.memory_percent):
                        memory_percent = p.memory_percent()
                    else:
                        memory_percent = p.get_memory_percent()
                except:
                    if verbose:
                        traceback.print_exc()
                        
                try:
                    if hasattr(p, "num_fds") and callable(p.num_fds):
                        num_fds = p.num_fds()
                    elif hasattr(p, "get_num_fds") and callable(p.get_num_fds):
                        num_fds = p.get_num_fds()
                except:
                    if verbose:
                        traceback.print_exc()
                
                try:
                    if hasattr(p, "io_counters") and callable(p.io_counters):
                        io_counters = p.io_counters.__dict__
                    elif hasattr(p, "get_io_counters") and callable(p.get_io_counters):
                        io_counters = p.get_io_counters().__dict__
                except:
                    if verbose:
                        traceback.print_exc()
                
                try:
                    if hasattr(p, "open_files") and callable(p.open_files):
                        open_files = p.open_files()
                    else:
                        open_files = p.get_open_files()
                except psutil.AccessDenied:
                    if verbose:
                        print ("'%s' Process is not allowing us to view the CPU Usage!" % name)
                    
                process = {
                    'name': name,
                    'exec': exe,
                    'pid': pid,
                    'status': status,
                    'username': username,
                    'cpu_percent': cpu_percent,
                    'memory': memory_info._asdict(),
                    'memory_percent': memory_percent,
                    'num_fds': num_fds,
                    'open_files': open_files,
                    'io_counters': io_counters,
                    'nice_level': nice
                }
                processes.append(process)
            except:
                if verbose:
                    traceback.print_exc()
        
        if system is 'windows':
            for win_process in psutil.win_service_iter():
                windows_services.append(win_process.as_dict())
                
        try:
            agent = {
                'last_updated': time.ctime(),
                'last_updated_timestamp': round(time.time()),
                'system': platform.system(),
                'kernel_version': platform.release(),
                'mac_version': platform.mac_ver()[0],
                'agent_version': agentVersion
            }
        except:
            agent = {
                'last_updated': time.ctime(),
                'last_updated_timestamp': round(time.time()),
                'agent_version': agentVersion
            }

        out = {
            'disks': disks,
            'disk_io': diskIO,
            'disk_io_total': diskIOTotal,
            'disk_io_total': diskIOTotal._asdict(),
    
            'cpu_total_percentage': cpuTotalPercentage,
            'cpu_percentage': cpuPercentage,
            'cpu_total_percentage_detailed': cpuTotalPercentageDetailed,
            'cpu_percentage_detailed': cpuPercentageDetailed,
            
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
    
    def do_GET(self):
        if 'auth' in config['default']:
            if str(config['default']['auth']).strip() and self.headers.get('Authorization') == None:
                self.do_AUTHHEAD()
                self.wfile.write('no auth header received'.encode())
            elif self.headers.get('Authorization') == 'Basic ' + config['default']['auth']:
                self._set_headers()
                self.wfile.write(json.dumps(cached_check_data).encode())
            elif str(config['default']['auth']).strip():
                self.do_AUTHHEAD()
                self.wfile.write(self.headers.get('Authorization').encode())
                self.wfile.write('not authenticated'.encode())
        else:
            self._set_headers()
            self.wfile.write(json.dumps(cached_check_data).encode())

    def log_message(self, format, *args):
        if verbose:
            print("%s - - [%s] %s" % (self.address_string(),self.log_date_time_string(),format%args))
        return

def collect_data_for_cache(check_interval):
    global cached_check_data
    time.sleep(1)
    if check_interval <= 0:
        check_interval = 5
    while True:
        cached_check_data = Collect().getData()
        time.sleep(check_interval)

def run_customcheck_command(check):
    if verbose:
        print('start custom check "' + check['name'] + '" with timeout ' + str(check['timeout']) + ' at '+str(round(time.time())))
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
                print('custom check "' + check['name'] + '" timed out')
            p.kill()    #not needed; just to be sure
            cached_customchecks_check_data[check['name']]['result'] = None
            cached_customchecks_check_data[check['name']]['error'] = 'TimeoutExpired'
            cached_customchecks_check_data[check['name']]['returncode'] = None
    
    except:
        if verbose:
            traceback.print_exc()
    
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
                print('custom check "' + check['name'] + '" stopped')
        except Exception as exc:
            if verbose:
                print('%r generated an exception: %s' % (check, exc))
    
    if len(cached_customchecks_check_data) > 0:
        cached_check_data['customchecks'] = cached_customchecks_check_data;

def collect_customchecks_data_for_cache(customchecks):
    max_workers = 4
    if 'DEFAULT' in customchecks:
        if 'max_worker_threads' in customchecks['DEFAULT']:
            max_workers = int(customchecks['DEFAULT']['max_worker_threads'])
    if verbose:
        print('Start thread pool with max. ' + str(max_workers) + ' workers')
    
    executor = futures.ThreadPoolExecutor(max_workers=max_workers)
    
    while True:
        need_to_be_checked = []
        for check_name in customchecks:
            if check_name is not 'DEFAULT':
                if 'command' in customchecks[check_name] and ('disabled' not in customchecks[check_name] or customchecks[check_name]['disabled'] == "false"):
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
    

def notify_oitc(oitc):
    global cached_check_data
    time.sleep(1)
    if oitc['url'].strip() and oitc['apikey'].strip() and int(oitc['interval']):
        noty_interval = int(oitc['interval'])
        if noty_interval <= 0:
            noty_interval = 5
        while True:
            time.sleep(noty_interval)
            if len(cached_check_data) > 0:
                try:
                    if isPython3:
                        data = bytes(urllib.parse.urlencode({'checkdata': cached_check_data}).encode())
                        req = urllib.request.Request(oitc['url'].strip())
                        req.add_header('Authorization', 'X-OITC-API '+oitc['apikey'].strip())
                        handler = urllib.request.urlopen(req, data)
                        if verbose:
                            print(handler.read().decode('utf-8'))
                    else:
                        data = bytes(urllib.urlencode({'checkdata': cached_check_data}).encode())
                        req = urllib2.Request(oitc['url'].strip())
                        req.add_header('Authorization', 'X-OITC-API '+oitc['apikey'].strip())
                        handler = urllib2.urlopen(req, data)
                        if verbose:
                            print(handler.read().decode('utf-8'))
                except:
                    if verbose:
                        traceback.print_exc()

def run(server_class=HTTPServer, handler_class=MyServer, config=config, ssl=False):
    server_address = ('', int(config['default']['port']))
    httpd = server_class(server_address, handler_class)
    protocol = 'http'
    
    if config['default']['address'] == "":
        config['default']['address'] = "127.0.0.1"
    if ssl:
        import ssl
        protocol = 'https'
        httpd.socket = ssl.wrap_socket(httpd.socket, keyfile=config['default']['keyfile'], certfile=config['default']['certfile'], server_side=True)
    if verbose:
        print("Server startet at %s://%s:%s with a check interval of %d seconds"%(protocol, config['default']['address'], str(config['default']['port']), int(config['default']['interval'])))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("")
        sys.exit(0)
        

def print_help():
    print('usage: ./oitc_agent.py -v -i <check interval seconds> -p <port number> -a <ip address> -c <config path> --certfile <certfile path> --keyfile <keyfile path> --auth <user>:<password> --oitc-url <url> --oitc-apikey <api key> --oitc-interval <seconds>')
    print('\nOptions and arguments (overwrite options in config file):')
    print('-i --interval <seconds>      : check interval in seconds')
    print('-p --port <number>           : webserver port number')
    print('-a --address <ip address>    : webserver ip address')
    print('-c --config <config path>    : config file path')
    print('--customchecks <file path>   : custom check config file path')
    print('--auth <user>:<password>     : enable http basic auth')
    print('-v --verbose                 : enable verbose mode')
    print('-h --help                    : print this help message and exit')
    print('\nAdd there parameters to enable transfer of check results to a openITCOCKPIT server:')
    print('--oitc-url <url>             : openITCOCKPIT url (https://demo.openitcockpit.io)')
    print('--oitc-apikey <api key>      : openITCOCKPIT api key')
    print('--oitc-interval <seconds>    : transfer interval in seconds')
    print('\nAdd there parameters to enable ssl encrypted http(s) server:')
    print('--certfile <certfile path>   : /path/to/cert.pem')
    print('--keyfile <keyfile path>     : /path/to/key.pem')
    print('\nSample config file:')
    print(sample_config)
    print('\nSample config file for custom check commands:')
    print(sample_customcheck_config)

if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:],"h:i:p:a:c:v",["interval=","port=","address=","config=","customchecks=","certfile=","keyfile=","auth=","oitc-url=","oitc-apikey=","oitc-interval=","verbose","help"])
    except getopt.GetoptError:
        print_help()
        sys.exit(2)
    
    if isPython3:
        config.read_string(sample_config)
    else:
        config.readfp(io.BytesIO(sample_config))
    
    for opt, arg in opts:
        if opt == "--customchecks":
            customchecks_configpath = str(arg)
        if opt in ("-c", "--config"):
            configpath = str(arg)
        elif opt in ("-v", "--verbose"):
            verbose = True
    
    if configpath is not "":
        if file_readable(configpath):
            with open(configpath, 'r') as configfile:
                if verbose:
                    print('load agent config file "' + configpath + '"')
                config.read_file(configfile)
        else:
            with open(configpath, 'w') as configfile:
                if verbose:
                    print('create new default agent config file "' + configpath + '"')
                config.write(configfile)
    
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
        elif opt == "--auth":
            config['default']['auth'] = str(base64.b64encode(arg.encode())).encode("utf-8")
        elif opt in ("-v", "--verbose"):
            config['default']['verbose'] = "true"
        elif opt == "--oitc-url":
            config['oitc']['url'] = str(arg)
            added_oitc_parameter += 1
        elif opt == "--oitc-apikey":
            config['oitc']['apikey'] = str(arg)
            added_oitc_parameter += 1
        elif opt == "--oitc-interval":
            config['oitc']['interval'] = str(arg)
            added_oitc_parameter += 1
    
    if config['default']['verbose'] in (1, "1", "true", "True", True):
        verbose = True
    else:
        verbose = False
    
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
    
    if 'oitc' in config and (config['oitc']['enabled'] in (1, "1", "true", "True", True) or added_oitc_parameter == 3):
        oitc_notification_thread(notify_oitc, (config['oitc'],))
    
    if customchecks_configpath != "":
        if file_readable(customchecks_configpath):
            with open(customchecks_configpath, 'r') as customchecks_configfile:
                if verbose:
                    print('load custom check config file "' + customchecks_configpath + '"')
                customchecks.read_file(customchecks_configfile)
            if customchecks:
                permanent_customchecks_check_thread(collect_customchecks_data_for_cache, (customchecks,))
    
    permanent_check_thread(collect_data_for_cache, (int(config['default']['interval']),))
    run(ssl=enableSSL)

