# openITCOCKPIT Monitoring Agent 2.0
Cross-Platform Monitoring Agent for openITCOCKPIT

1. [Installation](#Installation)
2. [Usage](#Usage)
3. [Sample files](#Sample-files)
4. [Build instructions](#Build-instructions)
5. [Export documentation as html](#Export-documentation-as-html)

---

Customer documentation: [https://docs.it-novum.com/display/ODE/openITCOCKPIT+Agent](https://docs.it-novum.com/display/ODE/openITCOCKPIT+Agent)

---

## Installation

## Productive installation

Require glibc >= 2.17

Supported & tested systems:
- macOS 10.14 (Mojave), 10.15 (Catalina)
- Ubuntu 14, 16, 18, 20
- Debian 8, 9, 10
- openSUSE Leap 42.3
- CentOS 7
- Arch Linux (2019.08.01)
- Windows 8.1, Windows 10, Windows Server 2016, Windows Server 2019


### Packages

Please visit the [release page](https://github.com/it-novum/openitcockpit-agent/releases) to download the latest or older versions.

#### Debian / Ubuntu

Install: `sudo apt install ./openitcockpit-agent_*_amd64.deb`

Uninstall: `sudo apt remove openitcockpit-agent`

#### Arch

Install: `sudo pacman -U openitcockpit-agent-*-x86_64.pkg.tar.xz`

Uninstall: `sudo pacman -R openitcockpit-agent`

#### CentOS / openSUSE

Install:  `rpm -i openitcockpit-agent-*.x86_64.rpm`

Uninstall:  `rpm -e openitcockpit-agent`

#### macOS

Install with double clicking the pkg installer file.

Install `sudo installer -pkg openitcockpit-agent-1.*.pkg -target / -verbose`

Uninstall `sudo installer -pkg openitcockpit-agent-uninstaller*.pkg -target / -verbose`

#### Windows

Install with double clicking the msi installer file.

Automated install:  `msiexec.exe /i openitcockpit-agent.msi INSTALLDIR="C:\Program Files\it-novum\openitcockpit-agent\" /qn`

Uninstall using the windows built-in graphical software manager.


## Developer installation

1. Clone this repository
```
git clone https://github.com/it-novum/openitcockpit-agent.git
cd openitcockpit-agent/
```

2. Create new Python virtual environment on Linux or macOS
```
python3 -m venv ./venv
. ./venv/bin/activate
```

2. Create new Python virtual environment on Windows (via PowerShell)
```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

python -m venv ./venv
. ./venv/Scripts/activate
```

3. Install dependencies on Linux or macOS
```
pip install -r requirements.txt
```

3. Install dependencies on Windows
```
pip install -r requirements.txt pywin32
```

4. Copy example config
```
cp example_config.cnf config.cnf
```

### Visual Studio Code 

Free Download: [https://code.visualstudio.com/](https://code.visualstudio.com/)

#### Plugins
 - [Python extension for Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=ms-python.python)

#### Setup Debugger
![VSCode debugger python](images/vscode_python_debugger.png)

### PyCharm Community 

Free Download: [https://www.jetbrains.com/pycharm/download/](https://www.jetbrains.com/pycharm/download/)

#### Setup Debugger
![Setup PyCharm debugger](images/setup_pycharm_debugger.png)

![run Pycharm debugger](images/run_pycharm_debugger.png)

---

## Usage

Default: ```python agent.py```

Custom: ```python oitc_agent.py -v -i <check interval seconds> -p <port number> -a <ip address> -c <config path> --certfile <certfile path> --keyfile <keyfile path> --auth <user>:<password> --oitc-url <url> --oitc-apikey <api key> --oitc-interval <seconds>```

Windows: ```python.exe agent.py```

#### Pull mode (publish data as json via a web server)

Default url to get check results: ```http://address:3333```

Default url to get current configuration: ```http://address:port/config```


Options (script start parameters overwrite options in config file):

| Option                             | Value         | Description                                                                                  |
|------------------------------------|---------------|----------------------------------------------------------------------------------------------|
| -i --interval                      | seconds       | check interval in seconds                                                                    |
| -p --port                          | number        | webserver port number                                                                        |
| -a --address                       | ip address    | webserver ip address                                                                         |
| -c --config                        | config path   | config file path (absolute path recommended)                                                 |
| --customchecks                     | file path     | custom check config file path (absolute path recommended)                                    |
| --auth                             | user:password | enable http basic auth                                                                       |
| -v --verbose                       |               | enable verbose mode (information/errors without stackstrace)                                 |
| -s --stacktrace                    |               | print stackstrace for possible exceptions                                                    |
| --config-update-mode               |               | enable configuration update mode threw post request and /config to get current configuration |
| --temperature-fahrenheit           |               | set temperature to fahrenheit if enabled (else use celsius)                                  |
| --dockerstats                      |               | enable docker status check                                                                   |
| --qemustats                        |               | enable qemu status check (linux only)                                                        |
| --no-cpustats                      |               | disable default cpu status check                                                             |
| --no-sensorstats                   |               | disable default sensor status check                                                          |
| --no-processstats                  |               | disable default process status check                                                         |
| --processstats-including-child-ids |               | add process child ids to the default process status check (computationally intensive)        |
| --no-netstats                      |               | disable default network status check                                                         |
| --no-diskstats                     |               | disable default disk status check                                                            |
| --no-netio                         |               | disable default network I/O calculation                                                      |
| --no-diskio                        |               | disable default disk I/O calculation                                                         |
| --no-winservices                   |               | disable default windows services status check (windows only)                                 |
| -h --help                          |               | print a help message and exit                                                                |


Add there parameters to enable ssl encrypted http(s) server:

| Option        | Value         | Description                                   |
|---------------|---------------|-----------------------------------------------|
| --certfile    | certfile path | /path/to/cert.pem (absolute path recommended) |
| --keyfile     | keyfile path  | /path/to/key.pem (absolute path recommended)  |
| --try-autossl |               | try to enable auto webserver ssl mode         |


File paths used for autossl (default: /etc/openitcockpit-agent/... or C:\Program Files\openitcockpit-agent\\...):

| Option             | Value     | Description                                        |
|--------------------|-----------|----------------------------------------------------|
| --autossl-csr-file | file path | /path/to/agent.csr (absolute path recommended)     |
| --autossl-crt-file | file path | /path/to/agent.crt (absolute path recommended)     |
| --autossl-key-file | file path | /path/to/agent.key (absolute path recommended)     |
| --autossl-ca-file  | file path | /path/to/server_ca.crt (absolute path recommended) |


Using ssl or autossl the URL change from http://address:port to https://address:port


Example:

You can create a self signed certificate and key file with this command

```
openssl req -nodes -new -x509 -keyout server.key -out server.cert
```

Create a .p12 file to import as certificate in your web browser (like Firefox) to be able to browse to the encrypted agent webserver
```
openssl req -nodes -new -x509 -keyout server.key -out server.cert
cat server.cert server.key > both.pem
openssl pkcs12 -export -in both.pem -out both.p12
```

#### Push mode (send data as POST request to a url endpoint)

Add there parameters (all required) to enable transfer of check results to a openITCOCKPIT server:

| Option          | Value     | Description                                       |
|-----------------|-----------|---------------------------------------------------|
| --oitc-hostuuid | host uuid | openITCOCKPIT host uuid                           |
| --oitc-url      | url       | openITCOCKPIT url (https://demo.openitcockpit.io) |
| --oitc-apikey   | api key   | openITCOCKPIT api key                             |
| --oitc-interval | seconds   | transfer interval in seconds                      |


Post data:
```
<?php echo 'Host ID: ' . $_POST['host'] . ' - ' . $_POST['checkdata'];
```

#### Update mode

You can update the agent config and customconfig on the fly by sending a post request with json formatted data

Default configuration update url: ```http://address:port```

Command Example:
```
curl -d @new_config.json http://0.0.0.0:3333 -u user:pass
```

---

## Sample files

Sample config file (with default script values):
```
[default]
  interval = 30
  port = 3333
  address = 0.0.0.0
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
```

Sample config file for custom check commands:
```
[default]
  # max_worker_threads should be increased with increasing number of custom checks
  # but consider: each thread needs (a bit) memory
  max_worker_threads = 8
[username]
  command = whoami
  interval = 30
  timeout = 5
  enabled = true
[uname]
  command = uname -a
  interval = 15
  timeout = 5
  enabled = false
```

JSON Example (file: new_config.json) for update mode and http://address:port/config result:
```
{
    "config": {
        "interval": 15,
        "port": 3333,
        "address": "0.0.0.0",
        "certfile": "/path",
        "keyfile": "",
        "try-autossl": "true",
        "autossl-folder": "",
        "autossl-csr-file": "/etc/openitcockpit-agent/agent.csr",
        "autossl-crt-file": "/etc/openitcockpit-agent/agent.crt",
        "autossl-key-file": "/etc/openitcockpit-agent/agent.key",
        "autossl-ca-file": "/etc/openitcockpit-agent/server_ca.crt",
        "verbose": "true",
        "stacktrace": "false",
        "config-update-mode": "false",
        "auth": "user:pass",
        "customchecks": "/path",
        "temperature-fahrenheit": "false",
        "dockerstats": "false",
        "qemustats": "false",
        "cpustats": "true",
        "sensorstats": "true",
        "processstats": "true",
        "processstats-including-child-ids": "false",
        "netstats": "true",
        "diskstats": "true",
        "netio": "true",
        "diskio": "true",
        "winservices": "true",
        "oitc-hostuuid": "hostid_123456",
        "oitc-url": "https://demo.openitcockpit.io",
        "oitc-apikey": "",
        "oitc-interval": 60,
        "oitc-enabled": "false"
    },
    "customchecks": {
        "default": {
            "max_worker_threads": 8
        },
        "username": {
            "command": "whoami",
            "interval": 30,
            "timeout": 5,
            "enabled": "1"
        },
        "uname": {
            "command": "uname -a",
            "interval": 15,
            "timeout": 5,
            "enabled": "0"
        }
    }
}
```

---

## Build instructions

Clone this repository to your filesystem and run the following commands in the repository folder

```
git clone https://github.com/it-novum/openitcockpit-agent.git
cd openitcockpit-agent
```

### Build Linux binary on CentOS 7

```
yum install python38-devel python38-pip libffi-devel gcc glibc ruby-devel make rpm-build rubygems rpm bsdtar
python3 -m venv ./python3-centos-env
./python3-centos-env/bin/activate
pip3 install -r requirements.txt
pyinstaller src/agent_nix.py -n openitcockpit-agent-python3 --onefile
./python3-centos-env/bin/deactivate

mv ./dist/openitcockpit-agent-python3 ./executables/openitcockpit-agent-python3.linux.bin
```


### Linux ARM64 on Debian 9 (Beta)

```
apt-get install python3-pip python3-venv build-essential libssl-dev libffi-dev python-dev zlib1g-dev
python3 -m venv ./python3-linux-env

./python3-linux-env/bin/activate
./python3-linux-env/bin/pip install wheel
./python3-linux-env/bin/pip install -r requirements.txt cryptography
sudo ./python3-linux-env/bin/python3 ./python3-linux-env/bin/pyinstaller src/agent_nix.py -n openitcockpit-agent-python3 --onefile
./python3-linux-env/bin/deactivate
sudo mv ./dist/openitcockpit-agent-python3 ./executables/openitcockpit-agent-python3-arm64.bin
sudo rm -r ./dist ./build ./__pycache__ openitcockpit-agent-python3.spec
sudo chmod +x ./executables/openitcockpit-agent-python3-arm64.bin
```

### Build Windows binary

Make sure python 3.9.x is installed. [Download](https://www.python.org/downloads/windows/)

Run via PowerShell
```
python.exe -m venv ./python3-windows-env
.\python3-windows-env\Scripts\activate.bat
.\python3-windows-env\Scripts\pip.exe install -r requirements.txt pywin32
.\python3-windows-env\Scripts\pyinstaller.exe src\agent_windows.py --onefile -n openitcockpit-agent-python3
.\python3-windows-env\Scripts\deactivate.bat

mv .\dist\openitcockpit-agent-python3.exe executables\openitcockpit-agent-python3.exe
```

### Build macOS binary

Make sure python3 is installed

```
brew install python
# export PATH="/usr/local/opt/python/libexec/bin:$PATH"
```

```
python3 -m venv ./python3-macos-env
./python3-macos-env/bin/activate
pip3 install -r requirements.txt
pyinstaller src/agent_nix.py -n openitcockpit-agent-python3 --onefile
./python3-macos-env/bin/deactivate




mv ./dist/openitcockpit-agent-python3 ./executables/openitcockpit-agent-python3.macos.bin
```


#### Test packages

```
sudo installer -pkg openitcockpit-agent-*.pkg -target / -verbose -dumplog
sudo installer -pkg openitcockpit-agent-uninstaller*.pkg -target / -verbose -dumplog
```


---

## Export documentation as html

```
pip3 install pdoc3
pdoc . --html --output-dir docs
rm -r ./__pycache__
```
