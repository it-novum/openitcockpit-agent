#!/bin/bash


# Exit on error
set -e

# Exit if variable is undefined
set -u

if [ -f /usr/bin/openitcockpit-agent-python3.linux.bin ]; then

    if [ -x "$(command -v systemctl)" ]; then
        systemctl stop openitcockpit-agent
        systemctl disable openitcockpit-agent
    else
        invoke-rc.d openitcockpit-agent stop
        update-rc.d -f openitcockpit-agent remove
    fi

fi

if [ -f /Applications/openitcockpit-agent/openitcockpit-agent-python3.macos.bin ]; then

    if [ -f /Applications/openitcockpit-agent/com.it-novum.openitcockpit.agent.plist ]; then
        /bin/launchctl stop com.it-novum.openitcockpit.agent
        /bin/launchctl unload -F /Applications/openitcockpit-agent/com.it-novum.openitcockpit.agent.plist
    fi
    
fi
