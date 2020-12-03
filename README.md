# openITCOCKPIT Monitoring Agent 2.0
Cross-Platform Monitoring Agent for openITCOCKPIT

1. [Installation](#Installation)
2. [Usage](#Usage)
3. [Sample files](#Sample-files)
4. [Define custom checks](#Define-custom-checks)
5. [Build instructions](#Build-instructions)
    - [Release a new version](#release-a-new-version-it-novum)
6. [Export documentation as html](#Export-documentation-as-html)

---

Customer documentation: [https://docs.it-novum.com/display/ODE/openITCOCKPIT+Agent](https://docs.it-novum.com/display/ODE/openITCOCKPIT+Agent)

---

## Installation

### Supported and tested operating systems
- Windows 8.1, Windows 10, Windows Server 2016, Windows Server 2019 (x64)
- macOS 10.14 (Mojave), 10.15 (Catalina) (x64)
- Ubuntu 14, 16, 18, 20 (x64)
- Debian 8, 9, 10 (x64)
- openSUSE Leap 42.3 (x64)
- CentOS 7 (x64)
- Arch Linux (2019.08.01) (x64)

On Linux based systems the openITCOCKPIT Monitoring Agent requires `glibc >= 2.17`

Your system or architecture is not in the list? Please see [Build instructions](#Build-instructions) to build the agent for your system.

### Packages

Please visit the [release page](https://github.com/it-novum/openitcockpit-agent/releases) to download the latest or older versions.

#### Debian / Ubuntu

Install
```
sudo apt install ./openitcockpit-agent_*_amd64.deb
```

Uninstall
```
sudo apt-get purge openitcockpit-agent
```

#### Red Hat Linux / CentOS / openSUSE

Install
```
rpm -i openitcockpit-agent-*.x86_64.rpm
```

Uninstall:
```
rpm -e openitcockpit-agent
```

#### Arch Linux 

Install
```
sudo pacman -U openitcockpit-agent-*-x86_64.pkg.tar.xz
```

Uninstall
```
sudo pacman -R openitcockpit-agent
```

#### Windows

##### GUI
Install with double clicking the msi installer file.

![openITCOCKPIT Monitoring Agent MSI installer](images/msi_install.png)

##### CLI
Automated install:
```
msiexec.exe /i openitcockpit-agent*.msi INSTALLDIR="C:\Program Files\it-novum\openitcockpit-agent\" /qn
```

Uninstall using the windows built-in graphical software manager.

#### macOS

##### GUI
Install with double clicking the pkg installer file.

![openITCOCKPIT Monitoring Agent PKG installer](images/pkg_install_macos.png)

##### CLI
Install
```
sudo installer -pkg openitcockpit-agent*.pkg -target / -verbose
```

Uninstall
```
sudo installer -pkg openitcockpit-agent-uninstaller*.pkg -target / -verbose
```

## Developer installation
Do you want to modify the source code of the openITCOCKPIT Monitoring Agent? If yes follow this guide to getting started. 

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

The entry point of the Agent for developing and debugging is always the file `agent_nix.py` (even on Windows!).

### Visual Studio Code 

Free Download: [https://code.visualstudio.com/](https://code.visualstudio.com/)

#### Plugins
 - [Python extension for Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=ms-python.python)

#### Setup Debugger
Open up `.vscode/launch.json` and set the full path to `config.cnf`
![VSCode launch.json](images/vscode_launch.png)

Configure the debugger and run the Agent
![VSCode debugger python](images/vscode_python_debugger.png)

Ignore changes in `launch.json`:
```
git update-index --assume-unchanged .vscode/launch.json
```

### PyCharm Community 

Free Download: [https://www.jetbrains.com/pycharm/download/](https://www.jetbrains.com/pycharm/download/)

#### Setup Debugger
![Setup PyCharm debugger](images/setup_pycharm_debugger.png)

![run Pycharm debugger](images/run_pycharm_debugger.png)


---

## Usage

Default: ```python agent_nix.py```

Custom: ```python agent_nix.py -v -i <check interval seconds> -p <port number> -a <ip address> -c <config path> --certfile <certfile path> --keyfile <keyfile path> --auth <user>:<password> --oitc-url <url> --oitc-apikey <api key> --oitc-interval <seconds>```

Windows: ```python.exe agent_nix.py```

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

## Configuration files

Please see the two example configuration files:
 - [config.cnf](https://github.com/it-novum/openitcockpit-agent/blob/development/example_config.cnf)
 - [customchecks.cnf](https://github.com/it-novum/openitcockpit-agent/blob/development/example_customchecks.cnf)

### Query current configuration from Agent as JSON
API Endpoint: `GET http://agent-address:port/config`
```json
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

## Define custom checks

openITCOCKPIT Monitoring Agent is 100% compatible to the
[Monitoring Plugins Development Guidelines](https://www.monitoring-plugins.org/doc/guidelines.html)
So you can use all monitoring plugins that work with: Naemon, Nagios, Shinken, Icinga 1 and Sensu

Custom checks will not get executed through an shell and have to be an execute file like a binary or a script.

### Windows PowerShell example

Example PowerShell script to run as custom check
```powershell
write-host "There are a total of $($args.count) arguments"
exit 1
```

Definition in `customchecks.cnf`
```
[check_powershell_script]
  command = powershell.exe -nologo -noprofile -File "C:\checks\powershell_example_plugin.ps1" arg1 arg2
  interval = 15
  timeout = 10
  enabled = true
```

### Windows binary example

Example binary (.exe) to run as custom check
```cpp
#include <iostream>
#include <stdlib.h>

int main(int argc,char* argv[]) {
  printf("This is an C++ example binary with. Number of arguments passed: %d", argc);
  exit(1);
  return 1;
}
```

Definition in `customchecks.cnf`
```
[check_binary]
  command = "C:\checks\check_dummy.exe" foo bar
  interval = 15
  timeout = 10
  enabled = true
```

### Linux/macOS bash example

Example bash script to run as custom check
```sh
#!/bin/bash
echo "There are a total of ${#} arguments"
exit 1
```

Definition in `customchecks.cnf`
```
[check_bash_script]
  command = /opt/checks/bash_example_plugin.sh arg1 arg2
  interval = 15
  timeout = 10
  enabled = true
```

### Linux/macOS binary example

Definition in `customchecks.cnf`
```
[check_binary]
  command = /usr/lib/nagios/plugins/check_users -w 5 -c 10
  interval = 15
  timeout = 10
  enabled = true
```

---

## Build instructions
Do you want to build your own executable of the openITCOCKPIT Agent (for an ARM based architecture for example),
or run the python code itself?
If yes, please follow the instructions

Clone this repository to your filesystem and run the following commands in the repository folder

```
git clone https://github.com/it-novum/openitcockpit-agent.git
cd openitcockpit-agent
```

### Build Linux binary on CentOS 7

```
yum install python38-devel python38-pip libffi-devel gcc glibc ruby-devel make rpm-build rubygems rpm bsdtar
python3 -m venv ./python3-centos-env
source ./python3-centos-env/bin/activate
pip3 install -r requirements.txt
pyinstaller agent_nix.py -n openitcockpit-agent-python3 --onefile
deactivate

mv ./dist/openitcockpit-agent-python3 ./executables/openitcockpit-agent-python3.linux.bin
```

### Build Linux binary on Ubuntu 20.04

```
yum install python38-devel python38-pip libffi-devel gcc glibc ruby-devel make rpm-build rubygems rpm bsdtar
apt-get install python3 python3-venv python3-pip python3-dev gcc build-essential

python3 -m venv ./python3-ubuntu-env
source ./python3-ubuntu-env/bin/activate
pip3 install -r requirements.txt
pyinstaller agent_nix.py -n openitcockpit-agent-python3 --onefile
deactivate

mv ./dist/openitcockpit-agent-python3 ./executables/openitcockpit-agent-python3.linux.bin
```

### Linux ARM64 on Debian 9 (Beta)

```
apt-get install python3-pip python3-venv build-essential libssl-dev libffi-dev python-dev zlib1g-dev
python3 -m venv ./python3-linux-env

source ./python3-linux-env/bin/activate
./python3-linux-env/bin/pip install wheel
./python3-linux-env/bin/pip install -r requirements.txt cryptography
sudo ./python3-linux-env/bin/python3 ./python3-linux-env/bin/pyinstaller agent_nix.py -n openitcockpit-agent-python3 --onefile
deactivate
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

#### Run Windows binary
```
.\executables\openitcockpit-agent-python3.exe debug
```

##### Run Windows binary as service
```
.\executables\openitcockpit-agent-python3.exe --startup delayed install
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
cd src
pyinstaller agent_nix.py --distpath ../dist -n openitcockpit-agent-python3 --onefile
cd ..
./python3-macos-env/bin/deactivate

mv ./dist/openitcockpit-agent-python3 ./executables/openitcockpit-agent-python3.macos.bin
```

### Run from python source code (Linux and macOS)
```
pip install -r requirements.txt
python agent_nix.py -c <FULL_PATH_TO>/config.cnf
```

### Run from python source code (Windows)
```
pip install -r requirements.txt pywin32
python agent_nix.py -c <FULL_PATH_TO>/config.cnf
```

#### Test packages

```
sudo installer -pkg openitcockpit-agent-*.pkg -target / -verbose -dumplog
sudo installer -pkg openitcockpit-agent-uninstaller*.pkg -target / -verbose -dumplog
```

## Release a new version (it-novum)
1. Increase version number in `src/agent_generic.py`
2. Increase version number in `version` file - **set both to the same number**
3. Push to `development` branch and Jenkins will build and publish a new **stable** release for all supported platforms.

3. Push to `development` branch and Jenkins will build and publish a new **nightly** release for all supported platforms.

To build MSI packages a _Professional_ License of _Advanced Installer_ is required.

---

## Export documentation as html

```
pip3 install pdoc3
pdoc . --html --output-dir docs
rm -r ./__pycache__
```

# Debugging

## Query the Agent using curl
```
curl -k -v https://xxx.xxx.xxx.xxx:3333 --cacert /opt/openitc/agent/server_ca.pem --key /opt/openitc/agent/server_ca.key --cert /opt/openitc/agent/server_ca.pem
```