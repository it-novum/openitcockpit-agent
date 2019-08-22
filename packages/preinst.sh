#!/bin/bash


# Exit on error
set -e

# Exit if variable is undefined
set -u

if [ -f /usr/bin/openitcockpit-agent-python3.linux.bin ]; then

    if [ -x "$(command -v systemctl)" ]; then
        systemctl stop openitcockpit-agent
    else
        invoke-rc.d openitcockpit-agent stop
    fi

fi

if [ -f /usr/bin/openitcockpit-agent-python3.macos.bin ]; then

    /bin/launchctl stop com.it-novum.openitcockpit.agent

fi
