import base64
import getopt
import json
import os
import sys
import configparser
import traceback
import time

if sys.platform == 'win32' or sys.platform == 'win64':
    import winreg

from src.color_output import ColorOutput
from src.filesystem import Filesystem
from src.help import Help
from src.operating_system import OperatingSystem


class Config:

    def __init__(self, agentVersion):
        self.agentVersion = agentVersion

        self.verbose = False
        self.stacktrace = False
        self.configpath = ""
        self.enableSSL = False
        self.autossl = True
        self.temperatureIsFahrenheit = False
        self.is_push_mode = False

        self.etc_agent_path = None

        self.config = configparser.ConfigParser(allow_no_value=True)
        self.customchecks = configparser.ConfigParser(allow_no_value=True)

        self.ColorOutput = ColorOutput()

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
                    self.ColorOutput.info('Load agent configuration file "%s"' % (self.configpath))
                    self.config.read_file(configfile)
            else:
                with open(self.configpath, 'w') as configfile:
                    self.ColorOutput.info('Create new default agent configuration file "%s"' % (self.configpath))
                    self.config.write(configfile)

        self.get_etc_path()
        self.build_autossl_defaults()

        for opt, arg in opts:
            if opt in ("-h", "--help"):
                help = Help()
                help.print_help()
                sys.exit(0)
            elif opt in ("-i", "--interval"):
                self.config.set('default', 'interval', str(arg))
            elif opt in ("-p", "--port"):
                self.config.set('default', 'port', str(arg))
            elif opt in ("-a", "--address"):
                self.config.set('default', 'address', str(arg))
            elif opt == "--certfile":
                self.config.set('default', 'certfile', str(arg))
            elif opt == "--keyfile":
                self.config.set('default', 'keyfile', str(arg))
            elif opt == "--try-autossl":
                self.config.set('default', 'try-autossl', 'true')
            elif opt == "--autossl-folder":
                self.config.set('default', 'autossl-folder', str(arg))
            elif opt == "--autossl-csr-file":
                self.config.set('default', 'autossl-csr-file', str(arg))
            elif opt == "--autossl-crt-file":
                self.config.set('default', 'autossl-crt-file', str(arg))
            elif opt == "--autossl-key-file":
                self.config.set('default', 'autossl-key-file', str(arg))
            elif opt == "--autossl-ca-file":
                self.config.set('default', 'autossl-ca-file', str(arg))
            elif opt == "--auth":
                self.config.set('default', 'auth', str(arg))
            elif opt in ("-v", "--verbose"):
                self.config.set('default', 'verbose', 'true')
            elif opt in ("-s", "--stacktrace"):
                self.config.set('default', 'stacktrace', 'true')
            elif opt == "--config-update-mode":
                self.config.set('default', 'config-update-mode', 'true')
            elif opt == "--temperature-fahrenheit":
                self.config.set('default', 'temperature-fahrenheit', 'true')
            elif opt == "--dockerstats":
                self.config.set('default', 'dockerstats', 'true')
            elif opt == "--qemustats":
                self.config.set('default', 'qemustats', 'true')
            elif opt == "--no-cpustats":
                self.config.set('default', 'cpustats', 'false')
            elif opt == "--no-sensorstats":
                self.config.set('default', 'sensorstats', 'false')
            elif opt == "--no-processstats":
                self.config.set('default', 'processstats', 'false')
            elif opt == "--processstats-including-child-ids":
                self.config.set('default', 'processstats-including-child-ids', 'true')
            elif opt == "--no-netstats":
                self.config.set('default', 'netstats', 'false')
            elif opt == "--no-diskstats":
                self.config.set('default', 'diskstats', 'false')
            elif opt == "--no-netio":
                self.config.set('default', 'netio', 'false')
            elif opt == "--no-diskio":
                self.config.set('default', 'diskio', 'false')
            elif opt == "--no-winservices":
                self.config.set('default', 'winservices', 'false')
            elif opt == "--oitc-hostuuid":
                self.config.set('oitc', 'hostuuid', str(arg))
            elif opt == "--oitc-url":
                self.config.set('oitc', 'url', str(arg))
            elif opt == "--oitc-apikey":
                self.config.set('oitc', 'apikey', str(arg))
            elif opt == "--oitc-interval":
                self.config.set('oitc', 'interval', str(arg))
            elif opt == "--customchecks":
                self.config.set('default', 'customchecks', str(arg))

        # loop again to consider default overwrite options
        for opt, arg in opts:
            if opt == "--disable-autossl":
                self.config.set('default', 'try-autossl', 'false')
                break

        self.verbose = self.config.getboolean('default', 'verbose')
        self.stacktrace = self.config.getboolean('default', 'stacktrace')
        self.autossl = self.config.getboolean('default', 'try-autossl')
        self.temperatureIsFahrenheit = self.config.getboolean('default', 'temperature-fahrenheit')

        # Determine if the Agent should run in PUSH mode
        if self.config.getboolean('oitc', 'enabled') is True:
            self.push_config = {
                'url': self.config.get('oitc', 'url').strip(),
                'apikey': self.config.get('oitc', 'apikey').strip(),
                'hostuuid': self.config.get('oitc', 'hostuuid').strip(),
                'interval': self.config.getint('oitc', 'interval', fallback=30)
            }

            if self.push_config['interval'] <= 0:
                self.push_config['interval'] = 30

            if self.push_config['url'] and self.push_config['apikey']:
                self.is_push_mode = True

        if self.config.get('default', 'autossl-folder', fallback='') != '':
            self.build_autossl_defaults()

        if 'auth' in self.config['default'] and str(self.config['default']['auth']).strip():
            if not self.is_base64(s=self.config['default']['auth']):
                self.config['default']['auth'] = str(base64.b64encode(self.config['default']['auth'].encode()), "utf-8")

        if self.config.get('default', 'certfile', fallback='') != '' and self.config.get('default', 'keyfile',
                                                                                         fallback='') != '':
            try:
                if Filesystem.file_readable(self.config.get('default', 'certfile')) and Filesystem.file_readable(
                        self.config.get('default', 'keyfile')):
                    self.enableSSL = True
                else:
                    self.ColorOutput.error('Could not read certificate or key file. Fall back to default http server.')


            except IOError:
                self.ColorOutput.error('Could not read certfile or keyfile. Fall back to default http server')

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
        etc_agent_path = self.get_etc_path()

        if self.config.get('default', 'autossl-folder', fallback='') != "":
            etc_agent_path = self.config.get('default', 'autossl-folder')

        if etc_agent_path.endswith(os.path.sep) is False:
            etc_agent_path = etc_agent_path + os.path.sep

        self.config.set('default', 'autossl-csr-file', etc_agent_path + 'agent.csr')
        self.config.set('default', 'autossl-crt-file', etc_agent_path + 'agent.crt')
        self.config.set('default', 'autossl-key-file', etc_agent_path + 'agent.key')
        self.config.set('default', 'autossl-ca-file', etc_agent_path + 'server_ca.crt')

    def get_custom_checks(self) -> dict:
        custom_checks_config_file = self.config.get('default', 'customchecks')
        if Filesystem.file_readable(custom_checks_config_file) is False:
            self.ColorOutput.error('Could not read customchecks configuration file %s' % (custom_checks_config_file))

        with open(custom_checks_config_file, 'r') as configfile:
            self.ColorOutput.info('Load agent custom checks configuration file "%s"' % (custom_checks_config_file))
            self.customchecks.read_file(configfile)

        custom_checks = {}

        for section in self.customchecks.sections():
            if section != 'default' and section != 'DEFAULT':

                enabled = self.customchecks.getboolean(section, 'enabled', fallback=False)

                if enabled:
                    custom_checks[section] = {
                        'command': self.customchecks.get(section, 'command', fallback='whoami'),
                        'interval': self.customchecks.getint(section, 'interval', fallback=60),
                        'timeout': self.customchecks.getint(section, 'timeout', fallback=5),
                        'enabled': enabled,
                        'last_check': 0,
                        'next_check': time.time(),
                        'running': False
                    }

        # Make this thread safe
        return custom_checks.copy()

    def get_config_as_dict(self) -> dict:
        """Build / Prepare config for a JSON object

        Build and returns the current configuration as object (dict).

        Returns
        -------
        data
            Dictionary object with the current configuration

        """
        data = {
            'config': {},
            'customchecks': {}
        }

        for key in self.config['default']:
            data['config'][key] = self.config['default'][key]

        for key in self.config['oitc']:
            data['config']['oitc-' + key] = self.config['oitc'][key]

        for custom_key in self.customchecks:
            data['customchecks'][custom_key] = {}
            if custom_key == 'default':
                data['customchecks'][custom_key]['max_worker_threads'] = self.customchecks[custom_key][
                    'max_worker_threads']
            else:
                for custom_key_option in self.customchecks[custom_key]:
                    data['customchecks'][custom_key][custom_key_option] = self.customchecks[custom_key][
                        custom_key_option]

        if data['config']['auth'] != "":
            data['config']['auth'] = str(base64.b64decode(data['config']['auth']), "utf-8")

        return data

    def set_new_config_from_dict(self, data) -> bool:
        """Function to check and update the agent configuration

        The POST Data Object will be parsed as valid json object.
        The configuration options are loaded into the configparser objects and will be written to the config files(if defined).
        After that an agent reload will be triggered to apply the new configuration files

        Parameters
        ----------
        data
            POST Data Object from webserver

        """
        try:
            jdata = json.loads(data.decode('utf-8'))

            for key in jdata:
                if key == 'config' and Filesystem.file_readable(self.configpath):
                    new_config = configparser.ConfigParser(allow_no_value=True)
                    new_config['default'] = {}
                    new_config['oitc'] = {}

                    if 'interval' in jdata[key]:
                        if int(jdata[key]['interval']) > 0:
                            new_config['default']['interval'] = str(jdata[key]['interval'])
                    if 'port' in jdata[key]:
                        if int(jdata[key]['port']) > 0:
                            new_config['default']['port'] = str(jdata[key]['port'])
                    if 'address' in jdata[key]:
                        new_config['default']['address'] = str(jdata[key]['address'])
                    if 'certfile' in jdata[key]:
                        new_config['default']['certfile'] = str(jdata[key]['certfile'])
                    if 'keyfile' in jdata[key]:
                        new_config['default']['keyfile'] = str(jdata[key]['keyfile'])
                    if 'try-autossl' in jdata[key]:
                        if jdata[key]['try-autossl'] in (1, "1", "true", "True"):
                            new_config['default']['try-autossl'] = "true"
                        else:
                            new_config['default']['try-autossl'] = "false"
                    if 'autossl-folder' in jdata[key]:
                        new_config['default']['autossl-folder'] = str(jdata[key]['autossl-folder'])
                    if 'autossl-csr-file' in jdata[key]:
                        new_config['default']['autossl-csr-file'] = str(jdata[key]['autossl-csr-file'])
                    if 'autossl-crt-file' in jdata[key]:
                        new_config['default']['autossl-crt-file'] = str(jdata[key]['autossl-crt-file'])
                    if 'autossl-key-file' in jdata[key]:
                        new_config['default']['autossl-key-file'] = str(jdata[key]['autossl-key-file'])
                    if 'autossl-ca-file' in jdata[key]:
                        new_config['default']['autossl-ca-file'] = str(jdata[key]['autossl-ca-file'])
                    if 'auth' in jdata[key]:
                        new_config['default']['auth'] = str(jdata[key]['auth'])
                    if 'verbose' in jdata[key]:
                        if jdata[key]['verbose'] in (1, "1", "true", "True"):
                            new_config['default']['verbose'] = "true"
                        else:
                            new_config['default']['verbose'] = "false"
                    if 'stacktrace' in jdata[key]:
                        if jdata[key]['stacktrace'] in (1, "1", "true", "True"):
                            new_config['default']['stacktrace'] = "true"
                        else:
                            new_config['default']['stacktrace'] = "false"
                    if 'config-update-mode' in jdata[key]:
                        if jdata[key]['config-update-mode'] in (1, "1", "true", "True"):
                            new_config['default']['config-update-mode'] = "true"
                        else:
                            new_config['default']['config-update-mode'] = "false"
                    if 'dockerstats' in jdata[key]:
                        if jdata[key]['dockerstats'] in (1, "1", "true", "True"):
                            new_config['default']['dockerstats'] = "true"
                        else:
                            new_config['default']['dockerstats'] = "false"
                    if 'qemustats' in jdata[key]:
                        if jdata[key]['qemustats'] in (1, "1", "true", "True"):
                            new_config['default']['qemustats'] = "true"
                        else:
                            new_config['default']['qemustats'] = "false"
                    if 'cpustats' in jdata[key]:
                        if jdata[key]['cpustats'] in (1, "1", "true", "True"):
                            new_config['default']['cpustats'] = "true"
                        else:
                            new_config['default']['cpustats'] = "false"
                    if 'sensorstats' in jdata[key]:
                        if jdata[key]['sensorstats'] in (1, "1", "true", "True"):
                            new_config['default']['sensorstats'] = "true"
                        else:
                            new_config['default']['sensorstats'] = "false"
                    if 'processstats' in jdata[key]:
                        if jdata[key]['processstats'] in (1, "1", "true", "True"):
                            new_config['default']['processstats'] = "true"
                        else:
                            new_config['default']['processstats'] = "false"
                    if 'processstats-including-child-ids' in jdata[key]:
                        if jdata[key]['processstats-including-child-ids'] in (1, "1", "true", "True"):
                            new_config['default']['processstats-including-child-ids'] = "true"
                        else:
                            new_config['default']['processstats-including-child-ids'] = "false"
                    if 'netstats' in jdata[key]:
                        if jdata[key]['netstats'] in (1, "1", "true", "True"):
                            new_config['default']['netstats'] = "true"
                        else:
                            new_config['default']['netstats'] = "false"
                    if 'diskstats' in jdata[key]:
                        if jdata[key]['diskstats'] in (1, "1", "true", "True"):
                            new_config['default']['diskstats'] = "true"
                        else:
                            new_config['default']['diskstats'] = "false"
                    if 'netio' in jdata[key]:
                        if jdata[key]['netio'] in (1, "1", "true", "True"):
                            new_config['default']['netio'] = "true"
                        else:
                            new_config['default']['netio'] = "false"
                    if 'diskio' in jdata[key]:
                        if jdata[key]['diskio'] in (1, "1", "true", "True"):
                            new_config['default']['diskio'] = "true"
                        else:
                            new_config['default']['diskio'] = "false"
                    if 'winservices' in jdata[key]:
                        if jdata[key]['winservices'] in (1, "1", "true", "True"):
                            new_config['default']['winservices'] = "true"
                        else:
                            new_config['default']['winservices'] = "false"
                    if 'systemdservices' in jdata[key]:
                        if jdata[key]['systemdservices'] in (1, "1", "true", "True"):
                            new_config['default']['systemdservices'] = "true"
                        else:
                            new_config['default']['systemdservices'] = "false"
                    if 'wineventlog' in jdata[key]:
                        if jdata[key]['wineventlog'] in (1, "1", "true", "True"):
                            new_config['default']['wineventlog'] = "true"
                        else:
                            new_config['default']['wineventlog'] = "false"
                    if 'wineventlog-logtypes' in jdata[key]:
                        new_config['default']['wineventlog-logtypes'] = str(jdata[key]['wineventlog-logtypes'])

                    if 'alfrescostats' in jdata[key]:
                        if jdata[key]['alfrescostats'] in (1, "1", "true", "True"):
                            new_config['default']['alfrescostats'] = "true"
                        else:
                            new_config['default']['alfrescostats'] = "false"
                    if 'alfresco-jmxuser' in jdata[key]:
                        new_config['default']['alfresco-jmxuser'] = str(jdata[key]['alfresco-jmxuser'])
                    if 'alfresco-jmxpassword' in jdata[key]:
                        new_config['default']['alfresco-jmxpassword'] = str(jdata[key]['alfresco-jmxpassword'])
                    if 'alfresco-jmxaddress' in jdata[key]:
                        new_config['default']['alfresco-jmxaddress'] = str(jdata[key]['alfresco-jmxaddress'])
                    if 'alfresco-jmxport' in jdata[key]:
                        new_config['default']['alfresco-jmxport'] = str(jdata[key]['alfresco-jmxport'])
                    if 'alfresco-jmxpath' in jdata[key]:
                        new_config['default']['alfresco-jmxpath'] = str(jdata[key]['alfresco-jmxpath'])
                    if 'alfresco-jmxquery' in jdata[key]:
                        new_config['default']['alfresco-jmxquery'] = str(jdata[key]['alfresco-jmxquery'])
                    if 'alfresco-javapath' in jdata[key]:
                        new_config['default']['alfresco-javapath'] = str(jdata[key]['alfresco-javapath'])

                    if 'customchecks' in jdata[key]:
                        if jdata[key]['customchecks'] not in (1, "1", "true", "True", 0, "0", "false", "False"):
                            new_config['default']['customchecks'] = str(jdata[key]['customchecks'])
                    if 'temperature-fahrenheit' in jdata[key]:
                        if jdata[key]['temperature-fahrenheit'] in (1, "1", "true", "True"):
                            new_config['default']['temperature-fahrenheit'] = "true"
                        else:
                            new_config['default']['temperature-fahrenheit'] = "false"
                    if 'oitc-hostuuid' in jdata[key]:
                        new_config['oitc']['hostuuid'] = str(jdata[key]['oitc-hostuuid'])
                    if 'oitc-url' in jdata[key]:
                        new_config['oitc']['url'] = str(jdata[key]['oitc-url'])
                    if 'oitc-apikey' in jdata[key]:
                        new_config['oitc']['apikey'] = str(jdata[key]['oitc-apikey'])
                    if 'oitc-interval' in jdata[key]:
                        new_config['oitc']['interval'] = str(jdata[key]['oitc-interval'])
                    if 'oitc-enabled' in jdata[key]:
                        if jdata[key]['oitc-enabled'] in (1, "1", "true", "True"):
                            new_config['oitc']['enabled'] = "true"
                        else:
                            new_config['oitc']['enabled'] = "false"

                    if self.configpath != "":
                        with open(self.configpath, 'w') as configfile:
                            self.ColorOutput.info('Save new configuration to %s' % (self.configpath))
                            new_config.write(configfile)
                    else:
                        self.ColorOutput.error('New configuration is invalid - aborting')

                elif key == 'config' and not Filesystem.file_readable(self.configpath):
                    self.ColorOutput.error('Agent configuration file %s is not readable ' % (self.configpath))

                if key == 'customchecks' and Filesystem.file_readable(self.config['default']['customchecks']):
                    new_customchecks = configparser.ConfigParser(allow_no_value=True)
                    new_customchecks.read_string(Help.sample_customcheck_config)

                    for customkey in jdata[key]:
                        new_customchecks[customkey] = {}

                        if customkey == 'default':
                            if 'max_worker_threads' in jdata[key][customkey]:
                                new_customchecks[customkey]['max_worker_threads'] = str(
                                    jdata[key][customkey]['max_worker_threads'])
                        else:
                            if 'command' in jdata[key][customkey]:
                                new_customchecks[customkey]['command'] = str(jdata[key][customkey]['command'])
                            if 'interval' in jdata[key][customkey]:
                                if int(jdata[key][customkey]['interval']) > 0:
                                    new_customchecks[customkey]['interval'] = str(jdata[key][customkey]['interval'])
                            if 'timeout' in jdata[key][customkey]:
                                if int(jdata[key][customkey]['timeout']) > 0:
                                    new_customchecks[customkey]['timeout'] = str(jdata[key][customkey]['timeout'])
                            if 'enabled' in jdata[key][customkey]:
                                new_customchecks[customkey]['enabled'] = "false"
                                if jdata[key][customkey]['enabled'] in (1, "1", "true", "True"):
                                    new_customchecks[customkey]['enabled'] = "true"

                    if self.config['default']['customchecks'] != "":
                        with open(self.config['default']['customchecks'], 'w') as configfile:
                            self.ColorOutput.info(
                                'Save new configuration to %s' % (self.config['default']['customchecks']))
                            new_customchecks.write(configfile)
                    else:
                        self.ColorOutput.error('New customchecks configuration is invalid - aborting')


                elif key == 'customchecks' and not Filesystem.file_readable(self.config['default']['customchecks']):
                    self.ColorOutput.error('Customchecks configuration file %s is not readable' % self.configpath)

            return True

        except Exception as e:
            self.ColorOutput.error('An error occurred while updating the agent configuration')
            print(e)

            if self.stacktrace:
                traceback.print_exc()

            return False

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

    def get_etc_path(self) -> str:
        if self.etc_agent_path is not None:
            return self.etc_agent_path

        operating_system = OperatingSystem()

        # Default path for Linux systems
        etc_agent_path = '/etc/openitcockpit-agent/'

        if operating_system.isMacos():
            etc_agent_path = '/Applications/openitcockpit-agent/'

        if operating_system.isWindows():
            # todo read path from windows registry
            etc_agent_path = 'C:' + os.path.sep + 'Program Files' + os.path.sep + 'it-novum' + os.path.sep + 'openitcockpit-agent' + os.path.sep
            try:
                registry_path = r'SOFTWARE\it-novum\InstalledProducts\openitcockpit-agent'
                registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path, 0, winreg.KEY_READ)
                value, regtype = winreg.QueryValueEx(registry_key, 'InstallLocation')
                winreg.CloseKey(registry_key)

                # Use path from registry (this can be changed in the msi installer)
                etc_agent_path = value
            except:
                print('Can not read path from registry. Using default one %s' % etc_agent_path)

        self.etc_agent_path = etc_agent_path
        return self.etc_agent_path
