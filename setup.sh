#!/bin/bash

function yes_or_no {
    if [ "$1" == "yes" ]; then
        default=0
    else
        default=1
    fi

    while true; do
        read -p "$2 [y/n]: " yn
        case $yn in
            [JjYy]*) return 0 ;;
            [Nn]*) return 1 ;;
            *) return $default ;;
        esac
    done
}

function write_initd_file {
    curl -sS "$download_url_initd" -o "$initd_file"
    sed -i "s/openitcockpit_agent=\\/usr\\/bin\\/openitcockpit-agent/openitcockpit_agent=\"\\/usr\\/bin\\/openitcockpit-agent\\ --config\\ ${config_file//\//\\/}\"/" "$initd_file"
    chmod +x "$initd_file"
}

function write_service_file {
    curl -sS "$download_url_service" -o "$service_file"
    sed -i "s/ExecStart=\\/usr\\/bin\\/openitcockpit-agent/ExecStart=\\/usr\\/bin\\/openitcockpit-agent\\ --config\\ ${config_file//\//\\/}/" "$service_file"
}

function write_launchd_file {
    curl -sS "$download_url_launchd" -o "$launchd_file"
    sed -i "" "s/\\/etc\\/openitcockpit-agent\\/config.conf/${config_file//\//\\/}/" "$launchd_file"
}

function write_config_file {
    curl -sS "$download_url_config" -o "$config_file"
}

function write_customchecks_file {
    curl -sS "$download_url_customchecks" -o "$customchecks_file"
}

function download_agent {
    #if [ "$OS" == "debian" ] || [ "$OS" == "ubuntu" ]; then
    #    curl -sS "$download_url_agent_linux" -o /usr/bin/openitcockpit-agent
    #elif [ "$OS" == "centos" ]; then
    if [ "$OS" == "darwin" ]; then
        curl -sS "$download_url_agent_macos" -o /usr/bin/openitcockpit-agent
    else
        curl -sS "$download_url_agent_centos_python3" -o /usr/bin/openitcockpit-agent
    fi
    #fi
    chmod +x /usr/bin/openitcockpit-agent
}

function agent_start {
    if [[ $use_initd -eq 0 ]] && [ "$OS" != "darwin" ]; then
        systemctl start openitcockpit-agent
    elif [ "$OS" != "darwin" ]; then
        $initd_file start
    elif [ "$OS" == "darwin" ]; then
        /bin/launchctl start com.it-novum.openitcockpit.agent
    fi
}

function agent_stop {
    if [[ $use_initd -eq 0 ]] && [ "$OS" != "darwin" ]; then
        systemctl stop openitcockpit-agent
    elif [ "$OS" != "darwin" ]; then
        $initd_file stop
    elif [ "$OS" == "darwin" ]; then
        /bin/launchctl stop com.it-novum.openitcockpit.agent
    fi
}

if [[ "$EUID" -ne 0 ]]; then
    echo "Sorry, you need to run this as root"
    exit
fi

if [ -f /etc/os-release ]; then
    # freedesktop.org and systemd
    . /etc/os-release
    OS=$ID
elif [[ -e /etc/debian_version ]]; then
    OS=debian
elif [[ -e /etc/centos-release || -e /etc/redhat-release ]]; then
    OS=centos
elif [ "$(uname)" == "Darwin" ]; then
    OS=darwin
fi

if [ "$OS" != "debian" ] && [ "$OS" != "ubuntu" ] && [ "$OS" != "centos" ] && [ "$OS" != "opensuse" ] && [ "$OS" != "darwin" ]; then
    echo "Looks like you aren't running this installer on Debian, Ubuntu, CentOS, openSUSE or macOS"
    exit
fi

service_file=/etc/systemd/system/openitcockpit-agent.service
initd_file=/etc/init.d/openitcockpit-agent
launchd_file=/Library/LaunchDaemons/com.it-novum.openitcockpit.agent.plist
use_initd=1

config_file=/etc/openitcockpit-agent/config.conf
customchecks_file=/etc/openitcockpit-agent/customchecks.conf

download_url_agent_linux="https://git.binsky.org/uploads/-/system/personal_snippet/9/c21c8d1956da3c98add64e098a32deda/openitcockpit-agent-python3.run"
download_url_agent_centos_python3="https://git.binsky.org/uploads/-/system/personal_snippet/9/f63cc269549221b2a9d1bf21c2c5569e/openitcockpit-agent-python3-old_glibc_centos.run"
download_url_agent_macos="https://git.binsky.org/uploads/-/system/personal_snippet/9/b666fbbd07e083689b91470f6c49f2c2/openitcockpit-agent-python3.macos"
download_url_config="https://git.binsky.org/uploads/-/system/personal_snippet/9/71c3a42780b3b84b650322b4220a0d83/config.cnf"
download_url_customchecks="https://git.binsky.org/uploads/-/system/personal_snippet/9/50a9caeacca7c440863af2fb0a6892fb/customchecks.cnf"
download_url_initd="https://git.binsky.org/uploads/-/system/personal_snippet/9/df317ebefa7dc2d59a9ea2091f3dcba4/openitcockpit-agent.initd"
download_url_service="https://git.binsky.org/uploads/-/system/personal_snippet/9/c31d48851ae7bcc6b51dd2b4ec67c9a4/openitcockpit-agent.service"
download_url_launchd="https://git.binsky.org/uploads/-/system/personal_snippet/9/94f681275cf9019fa673fb5a37d4d756/com.it-novum.openitcockpit.agent.plist"

if pgrep systemd-journal > /dev/null; then
    use_initd=0
fi

if [[ -e $service_file ]] || [[ -e $initd_file ]] || [[ -e $launchd_file ]]; then
    while :
    do
        echo ""
        echo "Looks like openITCOCKPIT agent is already installed"
        echo ""
        echo "What do you want to do?"
        echo "   1) Update openITCOCKPIT agent"
        echo "   2) Remove openITCOCKPIT agent"
        echo "   3) Exit"
        read -p "Select an option [1-3]: " option
        case $option in
            1)
            agent_stop
            download_agent
            agent_start
            echo "Agent successfully updated!"
            exit
            ;;
            2)
            agent_stop
            if [[ -e $service_file ]]; then
                systemctl disable openitcockpit-agent
                rm -f /usr/bin/openitcockpit-agent $service_file
            elif [[ -e $initd_file ]]; then
                /lib/systemd/systemd-sysv-install disable openitcockpit-agent
                rm -f /usr/bin/openitcockpit-agent $initd_file
            elif [[ -e $launchd_file ]]; then
                /bin/launchctl unload $launchd_file
                rm -f /usr/bin/openitcockpit-agent $launchd_file
            fi
            
            if [ -d "/etc/openitcockpit-agent" ]; then
                if yes_or_no "no" "Remove agent configuration folder '/etc/openitcockpit-agent'? (default: no)"; then
                    rm -rf /etc/openitcockpit-agent
                fi
            fi
            
            echo "Agent successfully removed!"
            exit
            ;;
            3)
            exit
            ;;
        esac
    done
else
    echo ""
    echo "Welcome to the openITCOCKPIT agent installer!"
    echo ""
    echo "I need to ask you a few questions during the setup."
    echo "You can leave the default options and just press enter if you are ok with them."
    echo ""

    read -r -p "Agent config file path: ($config_file) " -e custom_config_file

    if [ "$custom_config_file" != "" ]; then
        config_file=$custom_config_file
    fi

    read -r -p "Customcheck config file path: ($customchecks_file) " -e custom_customchecks_file

    if [ "$custom_customchecks_file" != "" ]; then
        customchecks_file=$custom_customchecks_file
    fi

    mkdir -p "$(dirname "$service_file")"
    mkdir -p "$(dirname "$config_file")"
    mkdir -p "$(dirname "$customchecks_file")"

    if [[ $use_initd -eq 0 ]] && [ "$OS" != "darwin" ]; then
        write_service_file
    elif [ "$OS" != "darwin" ]; then
        write_initd_file
    elif [ "$OS" == "darwin" ]; then
        write_launchd_file
    fi
    
    if [ ! -f "$config_file" ]; then
        write_config_file
    else
        if yes_or_no "no" "Overwrite existing agent config at ${config_file} (default: no)"; then
            write_config_file
        fi
    fi
    
    if [ ! -f "$customchecks_file" ]; then
        write_customchecks_file
    else
        if yes_or_no "no" "Overwrite existing customchecks config at ${customchecks_file} (default: no)"; then
            write_customchecks_file
        fi
    fi


    download_agent

    if [[ $use_initd -eq 0 ]] && [ "$OS" != "darwin" ]; then
        systemctl daemon-reload
        systemctl enable openitcockpit-agent
        systemctl start openitcockpit-agent
    elif [ "$OS" != "darwin" ]; then
        /lib/systemd/systemd-sysv-install enable openitcockpit-agent
        ${initd_file} start
    elif [ "$OS" == "darwin" ]; then
        /bin/launchctl load $launchd_file
        /bin/launchctl start $launchd_file
    fi
    

    echo ""
    echo "Agent successfully installed and started!"
    if [[ $use_initd -eq 0 ]] && [ "$OS" != "darwin" ]; then
        echo "Start agent with: systemctl start openitcockpit-agent"
        echo "After editing the config file restart the agent with: systemctl restart openitcockpit-agent"
    elif [ "$OS" != "darwin" ]; then
        echo "Start agent with: ${initd_file} start"
        echo "After editing the config file restart the agent with: ${initd_file} restart"
    elif [ "$OS" == "darwin" ]; then
        echo "Start agent with: /bin/launchctl start ${launchd_file}"
        echo "After editing the config file restart the agent with: /bin/launchctl stop ${launchd_file} && /bin/launchctl start ${launchd_file}"
    fi
    echo ""
fi

# yes_or_no "no" "Install openITCOCKPIT agent?"
#if (( $? != 0)); then
#	echo "Aborted!"
#	exit 0
#fi

