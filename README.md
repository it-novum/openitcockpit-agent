# openitcockpit-agent
Monitoring agent for openITCOCKPIT

1. [Installation](#Installation)
2. [Usage](#Usage)
2. [Sample files](#Sample-files)

## Installation
#### Dependencies

##### python3
- psutil >= 5.5.0
- configparser

##### python2
- psutil
- configparser
- futures
- subprocess32

### Windows
- Download & install latest python version (3.x) from https://www.python.org/downloads/windows/
- Open cmd and install dependencies: ```python.exe -m pip install psutil configparser```

### macOS (Darwin)
- Open console and install latest python version (3.x): ```brew install python3```
- Install dependencies: ```pip3 install psutil configparser```

### Linux (Debian / Ubuntu)
#### python3
- Install latest python version (3.x) and psutil >= 5.5.0: ```apt-get install python3 python3-psutil```
- Uninstall psutil pip package if version < 5.5.0: ```pip3 uninstall psutil```
- Install configparser dependency: ```pip3 install configparser```

#### python2
- Install python version (2.x) and psutil: ```apt-get install python python-psutil```
- Uninstall psutil pip package to use the newer apt package version: ```pip uninstall psutil```
- Install dependencies: ```pip install configparser futures subprocess32```

## Usage

Default: ```python oitc_agent.py```

Custom: ```python oitc_agent.py -v -i <check interval seconds> -p <port number> -a <ip address> -c <config path> --certfile <certfile path> --keyfile <keyfile path> --auth <user>:<password> --oitc-url <url> --oitc-apikey <api key> --oitc-interval <seconds>```

Windows: ```python.exe oitc_agent.py```

#### Pull mode (publish data as json threw a web server)
Options (script start parameters overwrite options in config file):

|option| value | description | 
| ------ | ------ | ----------- | 
|-i --interval       |seconds       |check interval in seconds     | 
|-p --port       |number       |webserver port number     | 
|-a --address       |ip address       |webserver ip address     | 
|-c --config       |config path       |config file path (absolute path recommended)     | 
|--customchecks       |file path       |custom check config file path (absolute path recommended)    | 
|--auth       |user:password       |enable http basic auth     | 
|-v --verbose       |       |enable verbose mode (information/errors without stackstrace)     | 
|--stacktrace       |       |print stackstrace for possible exceptions     | 
|-h --help       |       |print a help message and exit     | 

Add there parameters to enable ssl encrypted http(s) server:

|option| value | description | 
| ------ | ------ | ----------- | 
|--certfile       |certfile path       |/path/to/cert.pem (absolute path recommended)    | 
|--keyfile       |keyfile path       |/path/to/key.pem (absolute path recommended)    | 

URL change from http://address:port to https://address:port


Example:

You can create a self signed certificate and key file with this command

```
openssl req -nodes -new -x509 -keyout server.key -out server.cert
```

#### Push mode (send data as post request to a url endpoint)

Add there parameters to enable transfer of check results to a openITCOCKPIT server:

|option| value | description | 
| ------ | ------ | ----------- | 
|--oitc-url       |url       |openITCOCKPIT url (https://demo.openitcockpit.io)     | 
|--oitc-apikey       |api key       |openITCOCKPIT api key     | 
|--oitc-interval       |seconds       |transfer interval in seconds     | 

Post data:
```
<?php echo $_POST['checkdata'];
```

---

## Sample files

Sample config file (with default script values):
```
[default]
  interval = 30
  port = 3333
  address = 127.0.0.1
  certfile = 
  keyfile = 
  verbose = false
  stacktrace = false
  auth = 
  customchecks = 
[oitc]
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
