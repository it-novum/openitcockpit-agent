#!/bin/bash


# Exit on error
set -e

# Exit if variable is undefined
set -u


if [ -f /usr/bin/openitcockpit-agent-python3.linux.bin ]; then

    echo "Running post rm actions for linux systems..."

fi

if [ -f /usr/bin/openitcockpit-agent-python3.macos.bin ]; then

    set +e
    /bin/launchctl list | grep com.it-novum.openitcockpit.agent
    RC=$?
    if [ $RC -eq 0 ]; then
        /bin/launchctl stop com.it-novum.openitcockpit.agent
        /bin/launchctl unload -F /Library/LaunchDaemons/com.it-novum.openitcockpit.agent.plist
    fi
    set -e
    
    if [ -f /Library/LaunchDaemons/com.it-novum.openitcockpit.agent.plist ]; then
        rm /Library/LaunchDaemons/com.it-novum.openitcockpit.agent.plist
    fi
    
    if [ -f /Library/openitcockpit-agent/config.cnf ]; then
        rm /Library/openitcockpit-agent/config.cnf
    fi
    
    if [ -f /Library/openitcockpit-agent/customchecks.cnf ]; then
        rm /Library/openitcockpit-agent/customchecks.cnf
        
        rm -r /Library/openitcockpit-agent
    fi
    
    rm /usr/bin/openitcockpit-agent-python3.macos.bin

fi
