#!/bin/bash

# Exit on error
set -e

# Exit if variable is undefined
set -u

# Print all commands (debug option)
#set -x

### Define Variables ###

configFile="/etc/openitcockpit-agent/config.cnf"
customChecksConfigFile="/etc/openitcockpit-agent/customchecks.cnf"
OSXconfigFile="/Library/openitcockpit-agent/config.cnf"
OSXcustomChecksConfigFile="/Library/openitcockpit-agent/customchecks.cnf"

agentDownloadUrlLinuxBase="https://git.binsky.org/uploads/-/system/personal_snippet/9/c21c8d1956da3c98add64e098a32deda/openitcockpit-agent"


agentBinary="/usr/local/bin/openitcockpit-agent"

### Define functions ####
function stop_agent {
    if [ -x "$(command -v systemctl)" ]; then
        CMD="systemctl stop openitcockpit-agent"
    elif [ "$OS" == "Darwin" ]; then
        CMD="/bin/launchctl stop com.it-novum.openitcockpit.agent"
    else
        CMD="/etc/init.d/openitcockpit-agent stop"
    fi
    
    if [ "$isRoot" == "0" ]; then
        PREFIX="sudo "
        CMD="$PREFIX$CMD"
    fi
    $($CMD)
}

function start_agent {
    if [ -x "$(command -v systemctl)" ]; then
        CMD="systemctl start openitcockpit-agent"
    elif [ "$OS" == "Darwin" ]; then
        CMD="/bin/launchctl start com.it-novum.openitcockpit.agent"
    else
        CMD="/etc/init.d/openitcockpit-agent start"
    fi
    
    if [ "$isRoot" == "0" ]; then
        PREFIX="sudo "
        CMD="$PREFIX$CMD"
    fi
    $($CMD)
}

function download_agent {
    #URL="${agentDownloadUrlLinuxBase}.linux.bin"
    
    URL="https://git.binsky.org/uploads/-/system/personal_snippet/9/b666fbbd07e083689b91470f6c49f2c2/openitcockpit-agent-python3.macos"
    CMD="curl -fsSL $URL -o $agentBinary"
    
    if [ "$isRoot" == "0" ]; then
        PREFIX="sudo "
        CMD="$PREFIX$CMD"
    fi
    $($CMD)
    
    CMD="chmod +x $agentBinary"
    if [ "$isRoot" == "0" ]; then
        PREFIX="sudo "
        CMD="$PREFIX$CMD"
    fi
    $($CMD)
}

function create_systemd_service {
read -r -d '' content << EOM
[Unit]
Description=openITCOCKPIT Monitoring Agent
Documentation=https://openitcockpit.io
After=network.target

[Service]
User=root
Type=simple
Restart=on-failure
ExecStart=$agentBinary --config $configFile
StandardOutput=journal
StandardError=inherit

[Install]
WantedBy=multi-user.target
EOM

    CMD='echo "$content" > /lib/systemd/system/openitcockpit-agent.service'
    if [ "$isRoot" == "0" ]; then
        PREFIX="sudo "
        CMD="$PREFIX$CMD"
    fi
    $($CMD)

    CMD="systemctl daemon-reload"
    if [ "$isRoot" == "0" ]; then
        PREFIX="sudo "
        CMD="$PREFIX$CMD"
    fi
    $($CMD)
}

function create_launchd_service {

    enableConfig="0"
    if [ ! -f /Library/LaunchDaemons/com.it-novum.openitcockpit.agent.plist ]; then
        enableConfig="1"
    fi

content=$(cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
        <dict>
                <key>Label</key>
                <string>com.it-novum.openitcockpit.agent</string>
                <key>ProgramArguments</key>
                <array>
                        <string>$agentBinary</string>
                        <string>--config</string>
                        <string>$configFile</string>
                </array>
                <key>RunAtLoad</key>
                <true/>
        </dict>
</plist>
EOF
)

    if [ "$isRoot" == "0" ]; then
        # Looks strange? Required for macOS - dont touch!
        sudo sh -c "echo \"$content\" > /Library/LaunchDaemons/com.it-novum.openitcockpit.agent.plist"
    else
        echo "$content" > /Library/LaunchDaemons/com.it-novum.openitcockpit.agent.plist
    fi
    
    if [ "$enableConfig" == "1" ]; then
        CMD="/bin/launchctl load /Library/LaunchDaemons/com.it-novum.openitcockpit.agent.plist"
        if [ "$isRoot" == "0" ]; then
            PREFIX="sudo "
            CMD="$PREFIX$CMD"
        fi
        $($CMD)
    fi
}

function create_sysvinit_service {
    
    enableConfig="0"
    if [ ! -f /etc/init.d/openitcockpit-agent ]; then
        enableConfig="1"
    fi
    
read -r -d '' content << EOM
#!/bin/bash

### BEGIN INIT INFO
# Provides: openitcockpit-agent
# Required-Start: \$network \$remote_fs \$syslog
# Required-Stop:
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Description: openITCOCKPIT Monitoring Agent
### END INIT INFO

set -e
set -u

i=0
DAEMON="$agentBinary"
DAEMON_OPTS="--config $configFile"
PIDFILE=/var/run/openitcockpit-agent.pid
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

if [ \$# -lt 1 ]
then
    echo "\$0 <start|stop|restart|status>"
    exit 1
fi

case \$1 in
    start)
        echo "Starting openITCOCKPIT Monitoring Agent"
        start-stop-daemon --start --pidfile \$PIDFILE --make-pidfile --background --exec \$DAEMON --chuid root:root -- \$DAEMON_OPTS
    ;;

    stop)
        echo "Stopping openITCOCKPIT Monitoring Agent"
        start-stop-daemon --stop --quiet --oknodo --pidfile \$PIDFILE
        while start-stop-daemon --pidfile \$PIDFILE --status; do
            sleep .1
            if [ \$i -ge 100 ]; then
                echo "openITCOCKPIT Monitoring Agent stop failed"
                exit 1
            else
                i=\$(( i + 1 ))
                echo -n "."
            fi
        done
    ;;
    
    restart|reload|force-reload)
        echo "Restarting openITCOCKPIT Monitoring Agent"
        \$0 stop
        \$0 start
    ;;
    
    status)
        if start-stop-daemon --pidfile=\$PIDFILE --status
        then
            PID=`cat \$PIDFILE`
            echo "openITCOCKPIT Monitoring Agent is running (pid \$PID)."
            exit 0
        else
            echo "openITCOCKPIT Monitoring Agent is not running"
            exit 3
        fi
        ;;
    
    probe)
        echo restart
        exit 0
    ;;
    
    *)
        echo "Unknown command \$1."
        exit 1
    ;;
esac
EOM

    CMD='echo "$content" > /etc/init.d/openitcockpit-agent'
    if [ "$isRoot" == "0" ]; then
        PREFIX="sudo "
        CMD="$PREFIX$CMD"
    fi
    $($CMD)

    if [ "$enableConfig" == "1" ]; then
        CMD="update-rc.d -f openitcockpit-agent defaults"
        if [ "$isRoot" == "0" ]; then
            PREFIX="sudo "
            CMD="$PREFIX$CMD"
        fi
        $($CMD)
    fi
}

function update_init_config {
    if [ -x "$(command -v systemctl)" ]; then
        create_systemd_service;
    elif [ "$OS" == "Darwin" ]; then
        create_launchd_service;
    else
        create_sysvinit_service
    fi
}

function create_agent_config {
    if [ ! -f "$configFile" ]; then

content=$(cat <<EOF
[default]

# Determines in seconds how often the agent will schedule all internal checks
interval = 30

# Port of the Agents buil-in web server
port = 3333

# Bind address of the build-in web server
address = 127.0.0.1

# If a certificate file is given, the agent will switch to https only
# Example: /etc/ssl/certs/ssl-cert-snakeoil.pem
certfile =

# Private key file of the given TLS certificate
# Example: /etc/ssl/private/ssl-cert-snakeoil.key;
keyfile =

# Print most messages
verbose = false

# Print all messages with stacktrace
# For developers
stacktrace = false

# Enable remote read and write of THIS config file and custom checks defenition
# Examples:
#   Read config: curl http://127.0.0.1:3333/config
#   Write config: curl -X POST -d '{"config": {"interval": "60", "port": "3333", "address": "127.0.0.1", "certfile": "/etc/ssl/certs/ssl-cert-snakeoil.pem", "keyfile": "/etc/ssl/private/ssl-cert-snakeoil.key", "verbose": "true", "stacktrace": "false", "config-update-mode": "true", "auth": "", "customchecks": "", "temperature-fahrenheit": "false", "oitc-host": "", "oitc-url": "", "oitc-apikey": "", "oitc-interval": "60", "oitc-enabled": "false"}, "customchecks": {}}' http://127.0.0.1:3333/config
config-update-mode = false

# Enable Basic Authentication
# Disabled if blank
# Example: auth = user:password
auth =

# Remote Plugin Execution
# Path to config will where custom checks can be defined
customchecks = $customChecksConfigFile

# Return temperature values as fahrenheit
temperature-fahrenheit = false

# By default openITCOCKPIT will pull check results from the openITCOCKPIT Agent.
# In a Cloud environments or behind a NAT network it could become handy
# if the openITCOCKPIT Agent will push the results to the openITCOCKPIT Server
[oitc]

# Enable Push Mode
enabled = false

# The UUID of the Host.
# You can find this information in the openITCOCKPIT interface
# Example: 402357e4-dc34-4f5b-a86d-e59cfbb3ffe7
hostuuid =

# Address of the openITCOCKPIT Server
# Example: https://openitcockpit.io/receiver
url = 

# API-Key of the openITCOCKPIT Server
apikey =

# Determines in seconds how often the agent will push
# check results to the openITCOCKPIT Server
interval = 60
EOF
)

        if [ "$isRoot" == "0" ]; then
            # Looks strange? Required for macOS - dont touch!
            sudo sh -c "echo \"$content\" > $configFile"
        else
            echo "$content" > "$configFile"
        fi
    
    fi
}

function create_customchecks_config {
    if [ ! -f "$customChecksConfigFile" ]; then

content=$(cat <<EOF
[default]
  # max_worker_threads should be increased with increasing number of custom checks
  # but consider: each thread needs (a bit) memory
  max_worker_threads = 8

#[check_users]
#  command = /usr/lib/nagios/plugins/check_users -w 5 -c 10
#  interval = 30
#  timeout = 5
#  enabled = true

#[check_load]
#  command = /usr/lib/nagios/plugins/check_load -r -w .15,.10,.05 -c .30,.25,.20
#  interval = 60
#  timeout = 5
#  enabled = true
EOF
)
        
        if [ "$isRoot" == "0" ]; then
            # Looks strange? Required for macOS - dont touch!
            sudo sh -c "echo \"$content\" > $customChecksConfigFile"
        else
            echo "$content" > "$customChecksConfigFile"
        fi
    
    fi
}

### Installer code ###

isRoot="1"
if [ "$EUID" -ne "0" ]; then
    isRoot=0;
    echo "#######################################################"
    echo "# You are running this script as unprivileged user.   #"
    echo "# The installer will use sudo to execute commands     #"
    echo "# which require administrator privileges.             #"
    echo "#                                                     #"
    echo "# To avoid password prompts eg. if you plan to        #"
    echo "# automate the installation, please execute the       #"
    echo "# script as root.                                     #"
    echo "#######################################################"
    sleep 1
    
    if [ ! -x "$(command -v sudo)" ]; then
      echo 'Error: sudo is not installed.' >&2
      exit 1
    fi
fi

OS="UNKNOWN"
if [ -f /etc/redhat-release ]; then
    OS="RedHat"
fi
if [ -f /etc/SuSE-release ]; then
    OS="SuSe"
fi
if [ -f /etc/mandrake-release ]; then
    #Mandriva Linux
    OS="Mandrake"
fi
if [ -f /etc/debian_version ]; then
    OS="Debian"
fi

if [ "$(uname)" == "Darwin" ]; then
    OS="Darwin"
fi

if [ "$OS" == "UNKNOWN" ]; then
    echo "#######################################################"
    echo "#                 !!! WARNING !!!                     #"
    echo "# Installer could not detect operating system.        #"
    echo "# The installer will continue with CentOS settings.   #"
    echo "# This should work for most linux systems.            #"
    echo "#######################################################"
    echo ""
    echo "Will continue in 5 seconds or press ctrl+c to abort."
    sleep 1
    echo "4..."
    sleep 1
    echo "3..."
    sleep 1
    echo "2..."
    sleep 1
    echo "1..."
    sleep 1
    echo "Continue"
fi

if [ "$OS" == "Darwin" ]; then
    configFile="$OSXconfigFile"
    customChecksConfigFile="$OSXcustomChecksConfigFile"
    
    if [ ! -d "/Library/openitcockpit-agent" ]; then
        CMD="mkdir -p /Library/openitcockpit-agent"
        if [ "$isRoot" == "0" ]; then
            PREFIX="sudo "
            CMD="$PREFIX$CMD"
        fi
        $($CMD)
    fi
else
    if [ ! -d "/etc/openitcockpit-agent" ]; then
        CMD="mkdir -p /etc/openitcockpit-agent"
        if [ "$isRoot" == "0" ]; then
            PREFIX="sudo "
            CMD="$PREFIX$CMD"
        fi
        $($CMD)
    fi
fi

if [ -f "$agentBinary" ]; then
    stop_agent
fi

echo "Download openITCOCKPIT Agent binary"
download_agent;

echo "Check for default config"
create_agent_config;
create_customchecks_config;

echo "Enable openITCOCKPIT Agent service"
update_init_config;

echo "Start openITCOCKPIT Agent"
start_agent;

echo ""
echo "Installation/Update successfully"
echo ""

exit 0;
