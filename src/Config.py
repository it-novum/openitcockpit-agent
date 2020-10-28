import base64
import getopt
import os
import sys
import configparser

from src.Filesystem import Filesystem
from src.Help import Help
from src.OperatingSystem import OperatingSystem


class Config:

    def __init__(self, agentVersion):
        self.config = configparser.ConfigParser(allow_no_value=True)
        self.agentVersion = agentVersion

        self.verbose = False
        self.stacktrace = False
        self.added_oitc_parameter = 0
        self.configpath = ""
        self.enableSSL = False
        self.autossl = True
        self.temperatureIsFahrenheit = False

    def load_configuration(self):
        """Function to load/reload all configuration options

        Read and merge the start parameters and options from the configuration files (if configured).

        Decides if ssl will be enabled or not.

        """

        try:
            opts, args = getopt.getopt(sys.argv[1:], "h:i:p:a:c:vs",
                                       ["interval=", "port=", "address=", "config=", "customchecks=", "certfile=",
                                        "keyfile=", "auth=", "oitc-hostuuid=", "oitc-url=", "oitc-apikey=",
                                        "oitc-interval=", "config-update-mode", "temperature-fahrenheit", "try-autossl",
                                        "disable-autossl", "autossl-folder", "autossl-csr-file", "autossl-crt-file",
                                        "autossl-key-file", "autossl-ca-file", "dockerstats", "qemustats",
                                        "no-cpustats",
                                        "no-sensorstats", "no-processstats", "processstats-including-child-ids",
                                        "no-netstats", "no-diskstats", "no-netio", "no-diskio", "no-winservices",
                                        "verbose",
                                        "stacktrace", "help"])
        except getopt.GetoptError:
            help = Help()
            help.print_help()
            sys.exit(2)

        self.config = configparser.ConfigParser(allow_no_value=True)

        for opt, arg in opts:
            if opt in ("-c", "--config"):
                self.configpath = str(arg)
            elif opt in ("-v", "--verbose"):
                self.verbose = True
            elif opt in ("-s", "--stacktrace"):
                self.stacktrace = True

        if self.configpath != "":
            if Filesystem.file_readable(path=self.configpath):
                with open(self.configpath, 'r') as configfile:
                    print('Load agent configuration file "%s"' % (self.configpath))
                    self.config.read_file(configfile)
            else:
                with open(self.configpath, 'w') as configfile:
                    print('Create new default agent configuration file "%s"' % (self.configpath))
                    self.config.write(configfile)

        self.build_autossl_defaults()

        self.added_oitc_parameter = 0

        for opt, arg in opts:
            if opt in ("-h", "--help"):
                help = Help()
                help.print_help()
                sys.exit(0)
            elif opt in ("-i", "--interval"):
                self.config['default']['interval'] = str(arg)
            elif opt in ("-p", "--port"):
                self.config['default']['port'] = str(arg)
            elif opt in ("-a", "--address"):
                self.config['default']['address'] = str(arg)
            elif opt == "--certfile":
                self.config['default']['certfile'] = str(arg)
            elif opt == "--keyfile":
                self.config['default']['keyfile'] = str(arg)
            elif opt == "--try-autossl":
                self.config['default']['try-autossl'] = "true"
            elif opt == "--autossl-folder":
                self.config['default']['autossl-folder'] = str(arg)
            elif opt == "--autossl-csr-file":
                self.config['default']['autossl-csr-file'] = str(arg)
            elif opt == "--autossl-crt-file":
                self.config['default']['autossl-crt-file'] = str(arg)
            elif opt == "--autossl-key-file":
                self.config['default']['autossl-key-file'] = str(arg)
            elif opt == "--autossl-ca-file":
                self.config['default']['autossl-ca-file'] = str(arg)
            elif opt == "--auth":
                self.config['default']['auth'] = str(arg)
            elif opt in ("-v", "--verbose"):
                self.config['default']['verbose'] = "true"
            elif opt in ("-s", "--stacktrace"):
                self.config['default']['stacktrace'] = "true"
            elif opt == "--config-update-mode":
                self.config['default']['config-update-mode'] = "true"
            elif opt == "--temperature-fahrenheit":
                self.config['default']['temperature-fahrenheit'] = "true"
            elif opt == "--dockerstats":
                self.config['default']['dockerstats'] = "true"
            elif opt == "--qemustats":
                self.config['default']['qemustats'] = "true"
            elif opt == "--no-cpustats":
                self.config['default']['cpustats'] = "false"
            elif opt == "--no-sensorstats":
                self.config['default']['sensorstats'] = "false"
            elif opt == "--no-processstats":
                self.config['default']['processstats'] = "false"
            elif opt == "--processstats-including-child-ids":
                self.config['default']['processstats-including-child-ids'] = "true"
            elif opt == "--no-netstats":
                self.config['default']['netstats'] = "false"
            elif opt == "--no-diskstats":
                self.config['default']['diskstats'] = "false"
            elif opt == "--no-netio":
                self.config['default']['netio'] = "false"
            elif opt == "--no-diskio":
                self.config['default']['diskio'] = "false"
            elif opt == "--no-winservices":
                self.config['default']['winservices'] = "false"
            elif opt == "--oitc-hostuuid":
                self.config['oitc']['hostuuid'] = str(arg)
                self.added_oitc_parameter += 1
            elif opt == "--oitc-url":
                self.config['oitc']['url'] = str(arg)
                self.added_oitc_parameter += 1
            elif opt == "--oitc-apikey":
                self.config['oitc']['apikey'] = str(arg)
                self.added_oitc_parameter += 1
            elif opt == "--oitc-interval":
                self.config['oitc']['interval'] = str(arg)
                self.added_oitc_parameter += 1
            elif opt == "--customchecks":
                self.config['default']['customchecks'] = str(arg)

        # loop again to consider default overwrite options
        for opt, arg in opts:
            if opt == "--disable-autossl":
                self.config['default']['try-autossl'] = "false"
                break

        if self.config['default']['verbose'] in (1, "1", "true", "True", True):
            self.verbose = True
        else:
            self.verbose = False

        if self.config['default']['stacktrace'] in (1, "1", "true", "True", True):
            self.stacktrace = True
        else:
            self.stacktrace = False

        if self.config['default']['try-autossl'] in (1, "1", "true", "True", True):
            self.autossl = True
        else:
            self.autossl = False

        if self.config['default']['autossl-folder'] != "":
            self.build_autossl_defaults()

        if self.config['default']['temperature-fahrenheit'] in (1, "1", "true", "True", True):
            self.temperatureIsFahrenheit = True
        else:
            self.temperatureIsFahrenheit = False

        if 'auth' in self.config['default'] and str(self.config['default']['auth']).strip():
            if not self.is_base64(s=self.config['default']['auth']):
                self.config['default']['auth'] = str(base64.b64encode(self.config['default']['auth'].encode()), "utf-8")

        if self.config['default']['certfile'] != "" and self.config['default']['keyfile'] != "":
            try:
                if Filesystem.file_readable(self.config['default']['certfile']) and Filesystem.file_readable(
                        self.config['default']['keyfile']):
                    self.enableSSL = True
                else:
                    print("Could not read certfile or keyfile\nFall back to default http server")
                    if self.verbose:
                        print("Could not read certfile or keyfile\nFall back to default http server")


            except IOError:
                print("Could not read certfile or keyfile\nFall back to default http server")

    def build_autossl_defaults(self):
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
        operatingsystem = OperatingSystem()

        etc_agent_path = '/etc/openitcockpit-agent/'
        if operatingsystem.isWindows():
            etc_agent_path = 'C:' + os.path.sep + 'Program Files' + os.path.sep + 'it-novum' + os.path.sep + 'openitcockpit-agent' + os.path.sep

        if self.config['default']['autossl-folder'] != "":
            etc_agent_path = self.config['default']['autossl-folder'] + os.path.sep

        self.config['default']['autossl-csr-file'] = etc_agent_path + 'agent.csr'
        self.config['default']['autossl-crt-file'] = etc_agent_path + 'agent.crt'
        self.config['default']['autossl-key-file'] = etc_agent_path + 'agent.key'
        self.config['default']['autossl-ca-file'] = etc_agent_path + 'server_ca.crt'

    def is_base64(self, s):
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
