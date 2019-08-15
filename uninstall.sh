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

agentBinary="/usr/local/bin/openitcockpit-agent"

### Define functions ####
function stop_agent {
    if [ -x "$(command -v systemctl)" ]; then
        sudo systemctl stop openitcockpit-agent
        
        if [ -f "/lib/systemd/system/openitcockpit-agent.service" ]; then
            sudo rm "/lib/systemd/system/openitcockpit-agent.service"
        fi
        
        sudo systemctl daemon-reload
    elif [ "$OS" == "Darwin" ]; then
        sudo /bin/launchctl stop com.it-novum.openitcockpit.agent
        sudo /bin/launchctl unload com.it-novum.openitcockpit.agent
        
        if [ -f "/Library/LaunchDaemons/com.it-novum.openitcockpit.agent.plist" ]; then
            sudo rm "/Library/LaunchDaemons/com.it-novum.openitcockpit.agent.plist"
        fi
    else
        if [ -f "/etc/init.d/openitcockpit-agent" ]; then
            sudo /etc/init.d/openitcockpit-agent stop
            sudo update-rc.d -f openitcockpit-agent remove
            sudo rm /etc/init.d/openitcockpit-agent
        fi
    fi
}


### Uninstaller code ###

isRoot="1"
if [ "$EUID" -ne "0" ]; then
    isRoot=0;
    echo "#######################################################"
    echo "# You are running this script as unprivileged user.   #"
    echo "# The uninstaller will use sudo to execute commands   #"
    echo "# which require administrator privileges.             #"
    echo "#                                                     #"
    echo "# To avoid password prompts eg. if you plan to        #"
    echo "# automate the uninstall, please execute the          #"
    echo "# script as root.                                     #"
    echo "#######################################################"
    sleep 1
    
    if [ ! -x "$(command -v sudo)" ]; then
      echo 'Error: sudo is not installed.' >&2
      exit 1
    fi
fi

OS="Linux"
if [ "$(uname)" == "Darwin" ]; then
    OS="Darwin"
fi

if [ "$OS" == "Darwin" ]; then
    configFile="$OSXconfigFile"
    customChecksConfigFile="$OSXcustomChecksConfigFile"
fi

echo "Stop openITCOCKPIT Monitoring Agent"
stop_agent



echo "Delete configuration files"
if [ -f "$configFile" ]; then
    sudo rm "$configFile"
fi

if [ -f "$customChecksConfigFile" ]; then
    sudo rm "$customChecksConfigFile"
fi

if [ "$OS" == "Darwin" ]; then
    if [ -d "/Library/openitcockpit-agent" ]; then
        sudo rm -r /Library/openitcockpit-agent
    fi
else
    if [ -d "/etc/openitcockpit-agent" ]; then
        sudo rm -r /etc/openitcockpit-agent
    fi
fi

echo "Delete openITCOCKPIT Monitoring Agent binary"

if [ -f "$agentBinary" ]; then
    sudo rm "$agentBinary"
fi

echo ""
echo "Uninstall successfully"
echo ""

exit 0;
