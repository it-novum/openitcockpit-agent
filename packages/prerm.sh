#!/bin/bash


# Exit on error
set -e

# Exit if variable is undefined
set -u


if [ -f /usr/bin/openitcockpit-agent-python3.linux.bin ]; then

    set +e
    if [ -x "$(command -v systemctl)" ]; then
        /bin/systemctl -a | grep openitcockpit-agent >/dev/null
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

if [ -f /Applications/openitcockpit-agent/openitcockpit-agent-python3.macos.bin ]; then

    touch /Applications/openitcockpit-agent/tmp_runrm

    set +e
    /bin/launchctl list | grep com.it-novum.openitcockpit.agent >/dev/null
    RC=$?
    if [ "$RC" -eq 0 ]; then
        /bin/launchctl stop com.it-novum.openitcockpit.agent
        /bin/launchctl unload -F /Applications/openitcockpit-agent/com.it-novum.openitcockpit.agent.plist
    fi
    set -e
    
    rm /Applications/openitcockpit-agent/openitcockpit-agent-python3.macos.bin
    
    if [ -f /Applications/openitcockpit-agent/com.it-novum.openitcockpit.agent.plist ]; then
        rm /Applications/openitcockpit-agent/com.it-novum.openitcockpit.agent.plist
    fi
    
    if [ -h /Library/LaunchDaemons/com.it-novum.openitcockpit.agent.plist ]; then
        rm /Library/LaunchDaemons/com.it-novum.openitcockpit.agent.plist
    fi

    if [ -f /Applications/openitcockpit-agent/config.cnf ]; then
        rm /Applications/openitcockpit-agent/config.cnf
    fi
    
    if [ -f /Applications/openitcockpit-agent/customchecks.cnf ]; then
        rm /Applications/openitcockpit-agent/customchecks.cnf
    fi
    
    if [ -d /Applications/openitcockpit-agent ]; then
        rm -r /Applications/openitcockpit-agent
    fi

    if [ -d /private/etc/openitcockpit-agent ]; then
        rm -r /private/etc/openitcockpit-agent
    fi

fi
