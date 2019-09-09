#!/bin/bash


# Exit on error
set -e

# Exit if variable is undefined
set -u


if [ -f /usr/bin/openitcockpit-agent-python3.linux.bin ]; then

    set +e
    if [ -x "$(command -v systemctl)" ]; then
        /bin/systemctl -a | grep openitcockpit-agent
        RC=$?
        if [ "$RC" -eq 0 ]; then
            /bin/systemctl stop openitcockpit-agent
            /bin/systemctl disable openitcockpit-agent
        fi
        
        if [ -f /lib/systemd/system/openitcockpit-agent.service ]; then
            # Debian
            rm /lib/systemd/system/openitcockpit-agent.service
        fi
        if [ -f /usr/lib/systemd/system/openitcockpit-agent.service ]; then
            # ReadHat / Suse
            rm /usr/lib/systemd/system/openitcockpit-agent.service
        fi

    else
        invoke-rc.d openitcockpit-agent stop
        update-rc.d -f openitcockpit-agent remove
        
        if [ -f /etc/init.d/openitcockpit-agent ]; then
            rm /etc/init.d/openitcockpit-agent
        fi
    fi
    set -e

fi

if [ -f /usr/bin/openitcockpit-agent-python3.macos.bin ]; then

    touch /tmp/test123123123

    set +e
    /bin/launchctl list | grep com.it-novum.openitcockpit.agent
    RC=$?
    if [ "$RC" -eq 0 ]; then
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
