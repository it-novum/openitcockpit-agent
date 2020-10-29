class Help:
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

    def print_help(self):
        """Function to print the help

        Prints the help text and the default configuration (file) options to cli.

        """
        print(
            'usage: ./oitc_agent.py -v -i <check interval seconds> -p <port number> -a <ip address> -c <config path> --certfile <certfile path> --keyfile <keyfile path> --auth <user>:<password> --oitc-url <url> --oitc-apikey <api key> --oitc-interval <seconds>')
        print('\nOptions and arguments (overwrite options in config file):')
        print('-i --interval <seconds>                  : check interval in seconds')
        print('-p --port <number>                       : webserver port number')
        print('-a --address <ip address>                : webserver ip address')
        print('-c --config <config path>                : config file path')
        print(
            '--config-update-mode                     : enable config update mode threw post request and /config to get current configuration')
        print('--temperature-fahrenheit                 : set temperature to fahrenheit if enabled (else use celsius)')
        print('--dockerstats                            : enable docker status check')
        print('--qemustats                              : enable qemu status check (linux only)')
        print('--no-cpustats                            : disable default cpu status check')
        print('--no-sensorstats                         : disable default sensor status check')
        print('--no-processstats                        : disable default process status check')
        print(
            '--processstats-including-child-ids       : add process child ids to the default process status check (computationally intensive)')
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
        print(
            '\nFile paths used for autossl (default: /etc/openitcockpit-agent/... or C:\Program Files\openitcockpit-agent\...):')
        print(
            '--autossl-folder <path>                  : /default/folder/for/ssl/files (use instead of the following four arguments)')
        print('--autossl-csr-file <path>                : /path/to/agent.csr')
        print('--autossl-crt-file <path>                : /path/to/agent.crt')
        print('--autossl-key-file <path>                : /path/to/agent.key')
        print('--autossl-ca-file <path>                 : /path/to/server_ca.crt')
        print('\nSample config file:')
        print(self.sample_config)
        print('\nSample config file for custom check commands:')
        print(self.sample_customcheck_config)
