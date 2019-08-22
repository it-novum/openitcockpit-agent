#!/bin/bash

if [ ! -d "openitcockpit-agent" ]; then
    cd openitcockpit-agent/
    git pull
    cd ../
else
    git clone https://github.com/it-novum/openitcockpit-agent.git
fi


mkdir -p package_osx/usr/bin
mkdir -p package_osx/Library/openitcockpit-agent
mkdir -p package_osx/Library/LaunchDaemons

cp openitcockpit-agent/executables/openitcockpit-agent-python3.macos.bin package_osx/usr/bin/
cp openitcockpit-agent/exaple_config.cnf package_osx/Library/openitcockpit-agent/config.cnf
cp openitcockpit-agent/example_customchecks.cnf package_osx/Library/openitcockpit-agent/customchecks.cnf
cp openitcockpit-agent/packages/init/com.it-novum.openitcockpit.agent.plist package_osx/Library/LaunchDaemons/com.it-novum.openitcockpit.agent.plist

# MacOS x64 (only runs on macOS)
fpm -s dir -t rpm -C package --name oitc-agent --vendor "it-novum GmbH" --license "Apache License Version 2.0" --config-files Library/openitcockpit-agent --architecture native --maintainer "<daniel.ziegler@it-novum.com>" --description "openITCOCKPIT Monitoring Agent and remote plugin executor." --url "https://openitcockpit.io" --before-install openitcockpit-agent/packages/preinst.sh --after-install openitcockpit-agent/packages/postinst.sh --version "1.0.0"

